"""Tests for the config flow and the options flow."""

from __future__ import annotations

from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.stopwatch_plus.const import (
    CONF_INTERVAL,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType


def _duration(hours: int = 0, minutes: int = 0, seconds: int = 0) -> dict[str, int]:
    """Return a value as sent by the duration selector."""
    return {"hours": hours, "minutes": minutes, "seconds": seconds}


async def test_create_stopwatch(hass: HomeAssistant) -> None:
    """The user step creates an entry with the name as title and seconds as options."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Gaming",
            CONF_INTERVAL: _duration(minutes=30, seconds=15),
            CONF_UPDATE_INTERVAL: _duration(minutes=1),
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Gaming"
    assert result["options"] == {CONF_INTERVAL: 1815, CONF_UPDATE_INTERVAL: 60}
    assert hass.states.get("sensor.gaming_elapsed_time") is not None


async def test_invalid_durations_show_errors(hass: HomeAssistant) -> None:
    """Out-of-range durations are rejected with a message per field."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Gaming",
            CONF_INTERVAL: _duration(hours=25),
            CONF_UPDATE_INTERVAL: _duration(),
        },
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {
        CONF_INTERVAL: "interval_too_long",
        CONF_UPDATE_INTERVAL: "update_interval_out_of_range",
    }


async def test_change_options(
    hass: HomeAssistant, setup_stopwatch: MockConfigEntry
) -> None:
    """The options flow saves new options and reloads the stopwatch."""
    result = await hass.config_entries.options.async_init(setup_stopwatch.entry_id)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_INTERVAL: _duration(seconds=45),
            CONF_UPDATE_INTERVAL: _duration(seconds=10),
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert setup_stopwatch.options == {CONF_INTERVAL: 45, CONF_UPDATE_INTERVAL: 10}
    assert setup_stopwatch.state is config_entries.ConfigEntryState.LOADED
