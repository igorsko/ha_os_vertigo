"""Mode, heating level and timer selections."""

from homeassistant.components.select import SelectEntity
from homeassistant.exceptions import HomeAssistantError

from .const import HEAT_LEVEL, MODE, MODES, TIMER
from .entity import VertigoEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities(
        [
            VertigoSelect(entry.runtime_data, dp, name, options)
            for dp, name, options in (
                (MODE, "Modalità", MODES),
                (HEAT_LEVEL, "Livello riscaldamento", {str(i): str(i) for i in range(1, 5)}),
                (TIMER, "Timer", {"Disattivato": "0", **{f"{i} h": str(i) for i in range(1, 9)}}),
            )
        ]
    )


class VertigoSelect(VertigoEntity, SelectEntity):
    def __init__(self, coordinator, dp, name, options):
        super().__init__(coordinator, dp, name, (dp,))
        self.dp = dp
        self.mapping = options
        self._attr_options = list(options)

    @property
    def current_option(self):
        return next((label for label, wire in self.mapping.items() if wire == self.value(self.dp)), None)

    async def async_select_option(self, option):
        if option not in self.mapping:
            raise HomeAssistantError("Unsupported option")
        await self.coordinator.command({self.dp: self.mapping[option]})
