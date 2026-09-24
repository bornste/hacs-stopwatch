"""Config flow for the Stopwatch Plus integration."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import DurationSelector, TextSelector

from .const import (
    CONF_INTERVAL,
    CONF_UPDATE_INTERVAL,
    DEFAULT_INTERVAL,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_INTERVAL,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)


def _seconds_to_duration(seconds: int) -> dict[str, int]:
    """Convert seconds to the value format of the duration selector."""
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return {"hours": hours, "minutes": minutes, "seconds": secs}


def _duration_to_seconds(duration: dict[str, float]) -> int:
    """Convert a value of the duration selector to whole seconds."""
    return int(timedelta(**duration).total_seconds())


def _options_schema(options: dict[str, Any]) -> dict[vol.Marker, Any]:
    """Return the fields that can be changed later in the options."""
    return {
        vol.Required(
            CONF_INTERVAL,
            default=_seconds_to_duration(options.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        ): DurationSelector(),
        vol.Required(
            CONF_UPDATE_INTERVAL,
            default=_seconds_to_duration(
                options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
            ),
        ): DurationSelector(),
    }


def _validate_options(
    user_input: dict[str, Any],
) -> tuple[dict[str, int], dict[str, str]]:
    """Convert the durations to seconds and check their limits."""
    options = {
        CONF_INTERVAL: _duration_to_seconds(user_input[CONF_INTERVAL]),
        CONF_UPDATE_INTERVAL: _duration_to_seconds(user_input[CONF_UPDATE_INTERVAL]),
    }
    errors: dict[str, str] = {}
    if options[CONF_INTERVAL] > MAX_INTERVAL:
        errors[CONF_INTERVAL] = "interval_too_long"
    if not MIN_UPDATE_INTERVAL <= options[CONF_UPDATE_INTERVAL] <= MAX_UPDATE_INTERVAL:
        errors[CONF_UPDATE_INTERVAL] = "update_interval_out_of_range"
    return options, errors


class StopwatchPlusConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the creation of a new stopwatch."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> StopwatchPlusOptionsFlow:
        """Return the options flow."""
        return StopwatchPlusOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the name and the options of the new stopwatch."""
        errors: dict[str, str] = {}
        if user_input is not None:
            options, errors = _validate_options(user_input)
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data={}, options=options
                )

        schema = vol.Schema(
            {vol.Required(CONF_NAME): TextSelector(), **_options_schema({})}
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )


class StopwatchPlusOptionsFlow(OptionsFlowWithReload):
    """Change the options of an existing stopwatch; the entry reloads afterwards."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Show and save the options."""
        errors: dict[str, str] = {}
        if user_input is not None:
            options, errors = _validate_options(user_input)
            if not errors:
                return self.async_create_entry(data=options)

        schema = vol.Schema(_options_schema(dict(self.config_entry.options)))
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(schema, user_input),
            errors=errors,
        )
