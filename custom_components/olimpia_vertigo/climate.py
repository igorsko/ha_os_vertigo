"""Heater control with integer temperature targets."""

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.exceptions import HomeAssistantError

from .api import temperature_command
from .const import HEAT, POWER, TARGET, TEMPERATURE
from .entity import VertigoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([VertigoClimate(entry.runtime_data)])


class VertigoClimate(VertigoEntity, ClimateEntity):
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.HEAT]
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_min_temp = 1
    _attr_max_temp = 30
    _attr_target_temperature_step = 1
    _attr_precision = 1
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
    )

    def __init__(self, coordinator):
        super().__init__(coordinator, "climate", "Riscaldamento", (POWER, HEAT, TARGET))

    @property
    def hvac_mode(self):
        if type(self.value(POWER)) is not bool or type(self.value(HEAT)) is not bool:
            return None
        return HVACMode.HEAT if self.value(POWER) and self.value(HEAT) else HVACMode.OFF

    @property
    def target_temperature(self):
        return self.value(TARGET)

    @property
    def current_temperature(self):
        return self.value(TEMPERATURE)

    async def async_set_temperature(self, **kwargs):
        if ATTR_TEMPERATURE in kwargs:
            try:
                values = temperature_command(kwargs[ATTR_TEMPERATURE])
            except ValueError as err:
                raise HomeAssistantError(str(err)) from err
            await self.coordinator.command(values)

    async def async_set_hvac_mode(self, hvac_mode):
        if hvac_mode == HVACMode.HEAT:
            await self.coordinator.command({POWER: True, HEAT: True})
        elif hvac_mode == HVACMode.OFF:
            await self.coordinator.command({HEAT: False})
        else:
            raise HomeAssistantError("Unsupported heater mode")

    async def async_turn_on(self):
        await self.async_set_hvac_mode(HVACMode.HEAT)

    async def async_turn_off(self):
        await self.async_set_hvac_mode(HVACMode.OFF)
