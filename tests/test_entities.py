"""Entity commands checked against Home Assistant 2026.10 classes."""

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from homeassistant.components.climate import HVACMode
from homeassistant.exceptions import HomeAssistantError

from custom_components.olimpia_vertigo.climate import VertigoClimate
from custom_components.olimpia_vertigo.fan import VertigoFan
from custom_components.olimpia_vertigo.select import VertigoSelect
from custom_components.olimpia_vertigo.switch import VertigoSwitch


@pytest.fixture
def coordinator(entry, status):
    return SimpleNamespace(config_entry=entry, data=status, last_update_success=True, command=AsyncMock())


async def test_fan_manual_speed_exits_preset(coordinator):
    fan = VertigoFan(coordinator)
    await fan.async_set_percentage(50)
    coordinator.command.assert_awaited_once_with({"1": True, "2": "5", "3": "close"})


async def test_fan_zero_speed_turns_off(coordinator):
    await VertigoFan(coordinator).async_set_percentage(0)
    coordinator.command.assert_awaited_once_with({"1": False})


@pytest.mark.parametrize("speed", range(1, 10))
async def test_all_reported_speeds_round_trip(coordinator, speed):
    coordinator.data["1"] = True
    coordinator.data["2"] = str(speed)
    fan = VertigoFan(coordinator)
    await fan.async_set_percentage(fan.percentage)
    assert coordinator.command.call_args.args[0]["2"] == str(speed)


async def test_oscillation_bool(coordinator):
    await VertigoFan(coordinator).async_oscillate(True)
    coordinator.command.assert_awaited_once_with({"8": True})


async def test_climate_temperature_does_not_enable_heat(coordinator):
    await VertigoClimate(coordinator).async_set_temperature(temperature=25.0)
    coordinator.command.assert_awaited_once_with({"9": 25})


async def test_climate_heat_turns_on_master(coordinator):
    await VertigoClimate(coordinator).async_set_hvac_mode(HVACMode.HEAT)
    coordinator.command.assert_awaited_once_with({"1": True, "103": True})


async def test_climate_off_preserves_fan(coordinator):
    await VertigoClimate(coordinator).async_turn_off()
    coordinator.command.assert_awaited_once_with({"103": False})


def test_heater_state_requires_master_power(coordinator):
    coordinator.data["103"] = True
    climate = VertigoClimate(coordinator)
    assert climate.hvac_mode == HVACMode.OFF
    coordinator.data["1"] = True
    assert climate.hvac_mode == HVACMode.HEAT
    assert climate.current_temperature == 23


def test_unknown_modes_do_not_invent_state(coordinator):
    coordinator.data["3"] = "new-firmware-mode"
    assert VertigoFan(coordinator).preset_mode is None
    assert VertigoSelect(coordinator, "3", "Mode", {"Normale": "close"}).current_option is None


async def test_invalid_mode_not_sent(coordinator):
    with pytest.raises(HomeAssistantError):
        await VertigoFan(coordinator).async_set_preset_mode("unsupported")
    coordinator.command.assert_not_awaited()


async def test_beep_off_means_silent(coordinator):
    switch = VertigoSwitch(coordinator, "102", "Beep", "mdi:volume-high")
    await switch.async_turn_off()
    coordinator.command.assert_awaited_once_with({"102": False})


def test_missing_parameter_unavailable(coordinator):
    del coordinator.data["8"]
    assert not VertigoFan(coordinator).available


async def test_select_timer_wire_string(coordinator):
    select = VertigoSelect(coordinator, "11", "Timer", {"2 h": "2"})
    await select.async_select_option("2 h")
    coordinator.command.assert_awaited_once_with({"11": "2"})
