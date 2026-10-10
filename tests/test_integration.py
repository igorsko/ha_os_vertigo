"""Offline smoke test using HA's real loader, config entries and platforms."""

from pathlib import Path
import shutil

from homeassistant import bootstrap, config_entries, loader
from homeassistant.config_entries import ConfigEntryState
from homeassistant.setup import async_setup_component

from custom_components.olimpia_vertigo.const import DOMAIN


async def prepare(hass):
    source = Path(__file__).parents[1] / "custom_components"
    await hass.async_add_executor_job(
        shutil.copytree, source, Path(hass.config.config_dir) / "custom_components"
    )
    loader.async_setup(hass)
    hass.config.skip_pip = True
    hass.config_entries = config_entries.ConfigEntries(hass, {})
    await bootstrap.async_load_base_functionality(hass)
    assert await async_setup_component(hass, "homeassistant", {})
    assert await async_setup_component(hass, "persistent_notification", {})


async def test_load_all_platforms_and_unload(hass, entry, transport):
    await prepare(hass)
    hass.config_entries._entries[entry.entry_id] = entry
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.state == ConfigEntryState.LOADED
    states = [
        state
        for state in hass.states.async_all()
        if state.entity_id.startswith(
            (
                "fan.test_vertigo_",
                "climate.test_vertigo_",
                "switch.test_vertigo_",
                "select.test_vertigo_",
                "sensor.test_vertigo_",
            )
        )
    ]
    assert len(states) == 11
    assert all(state.state not in ("unknown", "unavailable") for state in states)
    coordinator = entry.runtime_data
    assert await hass.config_entries.async_unload(entry.entry_id)
    assert coordinator.closed
    transport.close.assert_called()


async def test_config_flow_validates_without_commands(hass, transport):
    await prepare(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    assert result["type"] == "form"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Test Vertigo",
            "device_id": "test-device",
            "host": "192.0.2.10",
            "local_key": "0123456789abcdef",
        },
    )
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    transport.set_multiple_values.assert_not_called()
    duplicate = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": "user"},
        data={
            "name": "Duplicate",
            "device_id": "test-device",
            "host": "192.0.2.10",
            "local_key": "0123456789abcdef",
        },
    )
    assert duplicate["type"] == "abort"
    assert duplicate["reason"] == "already_configured"
    await hass.config_entries.async_unload(result["result"].entry_id)


async def test_config_flow_invalid_key_and_failed_connection(hass, transport):
    await prepare(hass)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
    data = {"name": "Test", "device_id": "test-device", "host": "192.0.2.10", "local_key": "short"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["errors"] == {"base": "invalid_credentials"}
    transport.status.assert_not_called()
    data["local_key"] = "0123456789abcdef"
    transport.status.return_value = {"Error": "offline"}
    result = await hass.config_entries.flow.async_configure(result["flow_id"], data)
    assert result["errors"] == {"base": "cannot_connect"}
    transport.close.assert_called()
    hass.config_entries.flow.async_abort(result["flow_id"])


async def test_reconfigure_and_options_reload(hass, entry, transport):
    await prepare(hass)
    hass.config_entries._entries[entry.entry_id] = entry
    assert await hass.config_entries.async_setup(entry.entry_id)
    old = entry.runtime_data
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": "reconfigure", "entry_id": entry.entry_id}
    )
    assert result["step_id"] == "reconfigure"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"host": "192.0.2.11", "local_key": "fedcba9876543210"}
    )
    assert result["reason"] == "reconfigure_successful"
    await hass.async_block_till_done()
    assert old.closed
    assert entry.data["host"] == "192.0.2.11"
    assert entry.data["device_id"] == "test-device"
    result = await hass.config_entries.options.async_init(entry.entry_id)
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"poll_interval": 30})
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval.total_seconds() == 30
    assert await hass.config_entries.async_unload(entry.entry_id)
