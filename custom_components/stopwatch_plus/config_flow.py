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
from homeassistant.data_entry_flow import section
from homeassistant.helpers.selector import (
    BooleanSelector,
    DurationSelector,
    EntitySelector,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
)

from .const import (
    CONF_AUTO_RESET,
    CONF_AUTO_RESET_DELAY,
    CONF_GRACE_PERIOD,
    CONF_INTERVAL,
    CONF_RUNNING_STATES,
    CONF_SOURCE_ENTITY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_AUTO_RESET,
    DEFAULT_AUTO_RESET_DELAY,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_INTERVAL,
    DEFAULT_RUNNING_STATES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
    MAX_AUTO_RESET_DELAY,
    MAX_GRACE_PERIOD,
    MAX_INTERVAL,
    MAX_UPDATE_INTERVAL,
    MIN_UPDATE_INTERVAL,
)

# Collapsible section of the form that holds the source entity settings
SECTION_SOURCE = "source"

DURATION_OPTIONS = (
    CONF_INTERVAL,
    CONF_UPDATE_INTERVAL,
    CONF_GRACE_PERIOD,
    CONF_AUTO_RESET_DELAY,
)

DEFAULTS: dict[str, Any] = {
    CONF_INTERVAL: DEFAULT_INTERVAL,
    CONF_UPDATE_INTERVAL: DEFAULT_UPDATE_INTERVAL,
    CONF_RUNNING_STATES: DEFAULT_RUNNING_STATES,
    CONF_GRACE_PERIOD: DEFAULT_GRACE_PERIOD,
    CONF_AUTO_RESET: DEFAULT_AUTO_RESET,
    CONF_AUTO_RESET_DELAY: DEFAULT_AUTO_RESET_DELAY,
}


def _seconds_to_duration(seconds: int) -> dict[str, int]:
    """Convert seconds to the value format of the duration selector."""
    hours, rest = divmod(int(seconds), 3600)
    minutes, secs = divmod(rest, 60)
    return {"hours": hours, "minutes": minutes, "seconds": secs}


def _duration_to_seconds(duration: dict[str, float]) -> int:
    """Convert a value of the duration selector to whole seconds."""
    return int(timedelta(**duration).total_seconds())


def _options_schema(collapsed: bool) -> dict[vol.Marker, Any]:
    """Return the fields that can be changed later in the options."""
    source_schema = vol.Schema(
        {
            vol.Optional(CONF_SOURCE_ENTITY): EntitySelector(),
            vol.Optional(CONF_RUNNING_STATES): SelectSelector(
                SelectSelectorConfig(
                    options=DEFAULT_RUNNING_STATES,
                    multiple=True,
                    custom_value=True,
                    mode=SelectSelectorMode.DROPDOWN,
                )
            ),
            vol.Optional(CONF_GRACE_PERIOD): DurationSelector(),
            vol.Optional(CONF_AUTO_RESET): BooleanSelector(),
            vol.Optional(CONF_AUTO_RESET_DELAY): DurationSelector(),
        }
    )
    # All fields are optional: values that are not sent keep their current value
    return {
        vol.Optional(CONF_INTERVAL): DurationSelector(),
        vol.Optional(CONF_UPDATE_INTERVAL): DurationSelector(),
        vol.Optional(SECTION_SOURCE): section(source_schema, {"collapsed": collapsed}),
    }


def _form_values(options: dict[str, Any]) -> dict[str, Any]:
    """Return stored (flat, seconds) options as values for the form."""
    values = {**DEFAULTS, **options}
    for key in DURATION_OPTIONS:
        values[key] = _seconds_to_duration(values[key])
    source_keys = (
        CONF_SOURCE_ENTITY,
        CONF_RUNNING_STATES,
        CONF_GRACE_PERIOD,
        CONF_AUTO_RESET,
        CONF_AUTO_RESET_DELAY,
    )
    source = {key: values.pop(key) for key in source_keys if key in values}
    return {**values, SECTION_SOURCE: source}


def _validate_options(
    user_input: dict[str, Any], current: dict[str, Any]
) -> tuple[dict[str, Any], dict[str, str]]:
    """Flatten the form input, convert durations to seconds and check limits.

    Fields that are missing keep their current value. The source entity is only
    removed when the source section is sent without it (the field was cleared).
    """
    current_values = _form_values(current)
    values = {
        **current_values,
        **current_values[SECTION_SOURCE],
        **user_input,
        **user_input.get(SECTION_SOURCE, {}),
    }
    if (
        SECTION_SOURCE in user_input
        and CONF_SOURCE_ENTITY not in user_input[SECTION_SOURCE]
    ):
        values.pop(CONF_SOURCE_ENTITY, None)
    options: dict[str, Any] = {
        key: _duration_to_seconds(values[key]) for key in DURATION_OPTIONS
    }
    options[CONF_RUNNING_STATES] = [
        state.strip() for state in values.get(CONF_RUNNING_STATES, []) if state.strip()
    ]
    options[CONF_AUTO_RESET] = bool(values.get(CONF_AUTO_RESET, DEFAULT_AUTO_RESET))
    if values.get(CONF_SOURCE_ENTITY):
        options[CONF_SOURCE_ENTITY] = values[CONF_SOURCE_ENTITY]

    errors: dict[str, str] = {}
    if options[CONF_INTERVAL] > MAX_INTERVAL:
        errors[CONF_INTERVAL] = "interval_too_long"
    if not MIN_UPDATE_INTERVAL <= options[CONF_UPDATE_INTERVAL] <= MAX_UPDATE_INTERVAL:
        errors[CONF_UPDATE_INTERVAL] = "update_interval_out_of_range"
    # Fields inside a section are reported as general errors of the form
    if CONF_SOURCE_ENTITY in options and not options[CONF_RUNNING_STATES]:
        errors["base"] = "running_states_required"
    elif options[CONF_GRACE_PERIOD] > MAX_GRACE_PERIOD:
        errors["base"] = "grace_period_too_long"
    elif options[CONF_AUTO_RESET_DELAY] > MAX_AUTO_RESET_DELAY:
        errors["base"] = "auto_reset_delay_too_long"
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
            options, errors = _validate_options(user_input, {})
            if not errors:
                return self.async_create_entry(
                    title=user_input[CONF_NAME], data={}, options=options
                )

        schema = vol.Schema(
            {vol.Required(CONF_NAME): TextSelector(), **_options_schema(collapsed=True)}
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or _form_values({})
            ),
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
            options, errors = _validate_options(
                user_input, dict(self.config_entry.options)
            )
            if not errors:
                return self.async_create_entry(data=options)

        # The source section is open when a source entity is configured
        collapsed = CONF_SOURCE_ENTITY not in self.config_entry.options
        schema = vol.Schema(_options_schema(collapsed=collapsed))
        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                schema, user_input or _form_values(dict(self.config_entry.options))
            ),
            errors=errors,
        )
