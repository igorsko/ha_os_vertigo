"""Sanitized diagnostics without connection credentials or network identity."""


async def async_get_config_entry_diagnostics(hass, entry):
    coordinator = entry.runtime_data
    return {
        "integration_version": "0.1.0",
        "protocol": "3.3",
        "poll_interval": coordinator.update_interval.total_seconds(),
        "available": coordinator.last_update_success,
        "parameters": dict(coordinator.data or {}),
    }
