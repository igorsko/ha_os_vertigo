"""Fan power, nine speeds, oscillation and operating presets."""

import math

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.exceptions import HomeAssistantError

from .const import MODE, MODES, OSCILLATION, POWER, SPEED
from .entity import VertigoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([VertigoFan(entry.runtime_data)])


class VertigoFan(VertigoEntity, FanEntity):
    _attr_supported_features = (
        FanEntityFeature.SET_SPEED
        | FanEntityFeature.OSCILLATE
        | FanEntityFeature.PRESET_MODE
        | FanEntityFeature.TURN_ON
        | FanEntityFeature.TURN_OFF
    )
    _attr_speed_count = 9
    _attr_preset_modes = list(MODES)

    def __init__(self, coordinator):
        super().__init__(coordinator, "fan", "Ventilatore", (POWER, SPEED, OSCILLATION, MODE))

    @property
    def is_on(self):
        return self.value(POWER) if type(self.value(POWER)) is bool else None

    @property
    def percentage(self):
        if self.is_on is False:
            return 0
        if self.value(SPEED) not in tuple(map(str, range(1, 10))):
            return None
        return int(int(self.value(SPEED)) * 100 / 9)

    @property
    def oscillating(self):
        return self.value(OSCILLATION) if type(self.value(OSCILLATION)) is bool else None

    @property
    def preset_mode(self):
        return next((label for label, wire in MODES.items() if wire == self.value(MODE)), None)

    async def async_turn_on(self, percentage=None, preset_mode=None, **kwargs):
        values = {POWER: True}
        if percentage is not None:
            values.update(self._speed_values(percentage))
        if preset_mode is not None:
            if preset_mode not in MODES:
                raise HomeAssistantError("Unsupported fan mode")
            values[MODE] = MODES[preset_mode]
        await self.coordinator.command(values)

    async def async_turn_off(self, **kwargs):
        await self.coordinator.command({POWER: False})

    def _speed_values(self, percentage):
        if not 0 <= percentage <= 100:
            raise HomeAssistantError("Speed must be between 0 and 100")
        if percentage == 0:
            return {POWER: False}
        return {POWER: True, SPEED: str(math.ceil(percentage * 9 / 100)), MODE: "close"}

    async def async_set_percentage(self, percentage):
        await self.coordinator.command(self._speed_values(percentage))

    async def async_set_preset_mode(self, preset_mode):
        if preset_mode not in MODES:
            raise HomeAssistantError("Unsupported fan mode")
        await self.coordinator.command({MODE: MODES[preset_mode]})

    async def async_oscillate(self, oscillating):
        await self.coordinator.command({OSCILLATION: oscillating})
