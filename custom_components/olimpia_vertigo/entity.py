"""Shared device identity and availability."""

from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import CONF_DEVICE_ID, DOMAIN


class VertigoEntity(CoordinatorEntity):
    _attr_has_entity_name = True

    def __init__(self, coordinator, key, name, required):
        super().__init__(coordinator)
        entry = coordinator.config_entry
        device_id = entry.data[CONF_DEVICE_ID]
        self._attr_unique_id = f"{device_id}_{key}"
        self._attr_name = name
        self.required = required
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device_id)},
            name=entry.title,
            manufacturer="Olimpia Splendid",
            model="Vertigo",
        )

    @property
    def available(self):
        return super().available and all(dp in self.coordinator.data for dp in self.required)

    def value(self, dp):
        return (self.coordinator.data or {}).get(dp)
