"""One serialized local connection shared by every entity."""

import asyncio
from datetime import timedelta
import logging

from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import VertigoAPI, VertigoError
from .const import CONF_DEVICE_ID, CONF_INTERVAL, CONF_LOCAL_KEY, DOMAIN

_LOGGER = logging.getLogger(__name__)


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

    async def command(self, values):
        async with self.lock:
            if self.closed:
                raise HomeAssistantError("Vertigo connection is closed")
            try:
                self.snapshot = {**self.snapshot, **await self._run(self.api.command, values)}
            except VertigoError as err:
                self.async_set_update_error(UpdateFailed("Local command failed"))
                raise HomeAssistantError("Command failed; check the Vertigo state") from err
            self.async_set_updated_data(dict(self.snapshot))

    async def close(self):
        async with self.lock:
            self.closed = True
            await self._run(self.api.close)
