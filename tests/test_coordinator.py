"""Serialized executor access, cancellation, merging and shutdown."""

import asyncio
import threading

import pytest

from homeassistant.exceptions import HomeAssistantError

from custom_components.olimpia_vertigo.coordinator import VertigoCoordinator
from custom_components.olimpia_vertigo.diagnostics import async_get_config_entry_diagnostics


async def test_status_then_partial_command(hass, entry, transport):
    coordinator = VertigoCoordinator(hass, entry)
    coordinator.data = await coordinator._async_update_data()
    transport.status.return_value = {"dps": {"107": False}}
    await coordinator.command({"107": False})
    assert coordinator.data["107"] is False
    assert coordinator.data["10"] == 23
    await coordinator.close()


async def test_cancelled_io_keeps_lock(hass, entry, transport):
    started, release = threading.Event(), threading.Event()

    def slow_status():
        started.set()
        assert release.wait(5)
        return {"dps": {"1": False}}

    transport.status.side_effect = slow_status
    coordinator = VertigoCoordinator(hass, entry)
    task = asyncio.create_task(coordinator._async_update_data())
    await hass.async_add_executor_job(started.wait, 5)
    task.cancel()
    await asyncio.sleep(0)
    assert coordinator.lock.locked()
    release.set()
    with pytest.raises(asyncio.CancelledError):
        await task
    assert not coordinator.lock.locked()
    await coordinator.close()


async def test_failed_command_marks_unavailable(hass, entry, transport):
    coordinator = VertigoCoordinator(hass, entry)
    transport.set_multiple_values.return_value = {"Error": "offline"}
    with pytest.raises(HomeAssistantError):
        await coordinator.command({"1": True})
    assert not coordinator.last_update_success
    await coordinator.close()


async def test_closed_coordinator_rejects_commands(hass, entry, transport):
    coordinator = VertigoCoordinator(hass, entry)
    await coordinator.close()
    with pytest.raises(HomeAssistantError):
        await coordinator.command({"103": True})
    transport.set_multiple_values.assert_not_called()


async def test_diagnostics_omit_credentials(hass, entry, transport):
    coordinator = VertigoCoordinator(hass, entry)
    coordinator.data = await coordinator._async_update_data()
    entry.runtime_data = coordinator
    result = await async_get_config_entry_diagnostics(hass, entry)
    text = str(result)
    for value in entry.data.values():
        assert value not in text
    await coordinator.close()
