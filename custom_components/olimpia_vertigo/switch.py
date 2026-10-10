"""UV, acoustic signal and a directly visible oscillation switch."""

from homeassistant.components.switch import SwitchEntity

from .const import BEEP, OSCILLATION, UV
from .entity import VertigoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            VertigoSwitch(entry.runtime_data, dp, name, icon)
            for dp, name, icon in (
                (UV, "Lampada UV", "mdi:lightbulb"),
                (BEEP, "Segnale acustico", "mdi:volume-high"),
                (OSCILLATION, "Oscillazione", "mdi:swap-horizontal"),
            )
        ]
    )


class VertigoSwitch(VertigoEntity, SwitchEntity):
    def __init__(self, coordinator, dp, name, icon):
        super().__init__(coordinator, dp, name, (dp,))
        self.dp = dp
        self._attr_icon = icon

    @property
    def is_on(self):
        return self.value(self.dp) if type(self.value(self.dp)) is bool else None

    async def async_turn_on(self, **kwargs):
        await self.coordinator.command({self.dp: True})

    async def async_turn_off(self, **kwargs):
        await self.coordinator.command({self.dp: False})
