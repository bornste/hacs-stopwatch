"""Config flow for the Stopwatch Plus integration."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.const import CONF_NAME

from .const import DOMAIN

STEP_USER_SCHEMA = vol.Schema({vol.Required(CONF_NAME): str})


class StopwatchPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the creation of a new stopwatch."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the name of the new stopwatch."""
        if user_input is not None:
            # Further options (source entity, intervals, auto-reset) follow later.
            return self.async_create_entry(title=user_input[CONF_NAME], data={})

        return self.async_show_form(step_id="user", data_schema=STEP_USER_SCHEMA)
