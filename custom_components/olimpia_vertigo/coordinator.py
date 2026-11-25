"""One serialized local connection shared by every entity."""

import asyncio
from datetime import timedelta
import logging
from time import monotonic

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VertigoAPI, VertigoError
from .const import CONF_DEVICE_ID, CONF_INTERVAL, CONF_LOCAL_KEY, DOMAIN, HEAT, POWER

_LOGGER = logging.getLogger(__name__)
COOLDOWN_SECONDS = 30


class VertigoCoordinator(DataUpdateCoordinator):
    """Run blocking I/O off the event loop and serialize status and commands."""

    def __init__(self, hass, entry):
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            config_entry=entry,
            update_interval=timedelta(seconds=entry.options.get(CONF_INTERVAL, 15)),
            always_update=False,
        )
        self.api = VertigoAPI(entry.data[CONF_DEVICE_ID], entry.data["host"], entry.data[CONF_LOCAL_KEY])
        self.lock = asyncio.Lock()
        self.snapshot = {}
        self.closed = False
        self.cooldown_until = 0.0
        self.command_generation = 0
        self.shutdown_lock = asyncio.Lock()

    async def _run(self, method, *args):
        # A cancelled caller must not release the lock while its worker owns the socket.
        task = self.hass.async_add_executor_job(method, *args)
        try:
            return await asyncio.shield(task)
        except asyncio.CancelledError:
            try:
                await task
            except Exception:
                pass
            raise

    async def _async_update_data(self):
        async with self.lock:
            if self.closed:
                raise UpdateFailed("Connection closed")
            try:
                self.snapshot = {**self.snapshot, **await self._run(self.api.status)}
                return dict(self.snapshot)
            except VertigoError as err:
                raise UpdateFailed("Vertigo is unreachable or credentials are invalid") from err

    async def _read_locked(self):
        """Read fresh parameters rather than trusting a merged snapshot."""
        frame = await self._run(self.api.status)
        self.snapshot = {**self.snapshot, **frame}
        self.async_set_updated_data(dict(self.snapshot))
        return frame

    async def _write_locked(self, values):
        frame = await self._run(self.api.command, values)
        self.snapshot = {**self.snapshot, **frame}
        self.async_set_updated_data(dict(self.snapshot))
        return frame

    def _ensure_open(self):
        if self.closed:
            raise HomeAssistantError("Vertigo connection is closed")

    async def command(self, values):
        """Coordinate every master-power-off command, including zero fan speed."""
        try:
            if values.get(POWER) is False:
                if values != {POWER: False}:
                    raise HomeAssistantError("Unsupported combined shutdown command")
                async with self.shutdown_lock:
                    await self._shutdown()
                return
            async with self.lock:
                self._ensure_open()
                if values.get(POWER) is True or values.get(HEAT) is True:
                    # Explicit restart supersedes a pending full shutdown.
                    self.command_generation += 1
                if values.get(HEAT) is False:
                    # A later fan-off request must still honor the cooling period.
                    self.cooldown_until = max(self.cooldown_until, monotonic() + COOLDOWN_SECONDS)
                frame = await self._write_locked(values)
                if values.get(HEAT) is False:
                    if frame.get(HEAT) is not False:
                        raise HomeAssistantError("Heater shutdown was not confirmed")
                    self.cooldown_until = monotonic() + COOLDOWN_SECONDS
        except VertigoError as err:
            self.async_set_update_error(UpdateFailed("Local command failed"))
            raise HomeAssistantError("Command failed; check the Vertigo state") from err

    async def _shutdown(self):
        async with self.lock:
            self._ensure_open()
            generation = self.command_generation
            frame = await self._read_locked()
            if frame.get(POWER) is False:
                return
            if frame.get(POWER) is not True or type(frame.get(HEAT)) is not bool:
                raise HomeAssistantError("Cannot confirm heater and fan state")
            if frame[HEAT]:
                frame = await self._write_locked({HEAT: False})
                if frame.get(HEAT) is not False or frame.get(POWER) is not True:
                    raise HomeAssistantError("Cannot confirm heater off with fan running")
                self.cooldown_until = monotonic() + COOLDOWN_SECONDS
            delay = max(0.0, self.cooldown_until - monotonic())
            if not delay:
                await self._write_locked({POWER: False})
                return

        # Leave polling and explicit restart commands responsive during cooling.
        await asyncio.sleep(delay)
        async with self.lock:
            self._ensure_open()
            if generation != self.command_generation:
                return
            if monotonic() < self.cooldown_until:
                raise HomeAssistantError("Cooling period changed; request shutdown again")
            frame = await self._read_locked()
            if frame.get(POWER) is False:
                return
            if frame.get(POWER) is not True or frame.get(HEAT) is not False:
                raise HomeAssistantError("Heater or fan state changed during cooling")
            await self._write_locked({POWER: False})

    async def close(self):
        async with self.lock:
            self.closed = True
            await self._run(self.api.close)
