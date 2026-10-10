"""Olimpia Splendid Vertigo local integration."""

from homeassistant.const import Platform

from .coordinator import VertigoCoordinator

PLATFORMS = [Platform.FAN, Platform.CLIMATE, Platform.SWITCH, Platform.SELECT, Platform.SENSOR]


async def async_setup_entry(hass, entry):
    coordinator = VertigoCoordinator(hass, entry)
    try:
        await coordinator.async_config_entry_first_refresh()
        entry.runtime_data = coordinator
        await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    except BaseException:
        await coordinator.close()
        raise
    entry.async_on_unload(entry.add_update_listener(async_reload_entry))
    return True


async def async_unload_entry(hass, entry):
    if await hass.config_entries.async_unload_platforms(entry, PLATFORMS):
        await entry.runtime_data.close()
        return True
    return False


async def async_reload_entry(hass, entry):
    await hass.config_entries.async_reload(entry.entry_id)
