"""Ambient temperature, countdown and raw fault bitmap."""

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTemperature, UnitOfTime

from .const import FAULT, REMAINING, TEMPERATURE
from .entity import VertigoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            VertigoSensor(entry.runtime_data, dp, name, unit, device_class)
            for dp, name, unit, device_class in (
                (
                    TEMPERATURE,
                    "Temperatura ambiente",
                    UnitOfTemperature.CELSIUS,
                    SensorDeviceClass.TEMPERATURE,
                ),
                (REMAINING, "Timer residuo", UnitOfTime.MINUTES, SensorDeviceClass.DURATION),
                (FAULT, "Codice guasto", None, None),
            )
        ]
    )


class VertigoSensor(VertigoEntity, SensorEntity):
    def __init__(self, coordinator, dp, name, unit, device_class):
        super().__init__(coordinator, dp, name, (dp,))
        self.dp = dp
        self._attr_native_unit_of_measurement = unit
        self._attr_device_class = device_class
        if dp == TEMPERATURE:
            self._attr_state_class = SensorStateClass.MEASUREMENT
        if dp == FAULT:
            self._attr_entity_category = EntityCategory.DIAGNOSTIC

    @property
    def native_value(self):
        value = self.value(self.dp)
        return value if type(value) in (int, float) else None
