"""Manual local credentials with a read-only connection check."""

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_HOST, CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .api import VertigoAPI, VertigoError, validate_credentials
from .const import CONF_DEVICE_ID, CONF_INTERVAL, CONF_LOCAL_KEY, DOMAIN, POWER


def credentials_schema(defaults=None, reconfigure=False):
    defaults = defaults or {}
    fields = {
        vol.Required(CONF_HOST, default=defaults.get(CONF_HOST, "")): str,
        vol.Required(CONF_LOCAL_KEY): selector.TextSelector(
            selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
        ),
    }
    if not reconfigure:
        fields = {
            vol.Required(CONF_NAME, default="Vertigo"): str,
            vol.Required(CONF_DEVICE_ID): str,
            **fields,
        }
    return vol.Schema(fields)


def check_connection(data):
    api = VertigoAPI(data[CONF_DEVICE_ID], data[CONF_HOST], data[CONF_LOCAL_KEY])
    try:
        result = api.status()
        if type(result.get(POWER)) is not bool:
            raise VertigoError("Unsupported device")
    finally:
        api.close()


class VertigoConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def _validate(self, data):
        try:
            validate_credentials(data[CONF_DEVICE_ID], data[CONF_HOST], data[CONF_LOCAL_KEY])
        except ValueError:
            return {"base": "invalid_credentials"}
        try:
            await self.hass.async_add_executor_job(check_connection, data)
        except VertigoError:
            return {"base": "cannot_connect"}
        return {}

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            user_input = dict(user_input)
            user_input[CONF_DEVICE_ID] = user_input[CONF_DEVICE_ID].strip()
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            await self.async_set_unique_id(user_input[CONF_DEVICE_ID])
            self._abort_if_unique_id_configured()
            errors = await self._validate(user_input)
            if not errors:
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)
        return self.async_show_form(step_id="user", data_schema=credentials_schema(), errors=errors)

    async def async_step_reconfigure(self, user_input=None):
        entry = self._get_reconfigure_entry()
        errors = {}
        if user_input is not None:
            user_input = dict(user_input)
            user_input[CONF_HOST] = user_input[CONF_HOST].strip()
            errors = await self._validate({**entry.data, **user_input})
            if not errors:
                return self.async_update_reload_and_abort(entry, data_updates=user_input)
        return self.async_show_form(
            step_id="reconfigure", data_schema=credentials_schema(entry.data, True), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return VertigoOptionsFlow()


class VertigoOptionsFlow(config_entries.OptionsFlow):
    async def async_step_init(self, user_input=None):
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_INTERVAL, default=self.config_entry.options.get(CONF_INTERVAL, 15)
                    ): vol.All(vol.Coerce(int), vol.Range(min=10, max=120)),
                }
            ),
        )
