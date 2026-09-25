"""Tests for the config flow and the options flow."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.stopwatch_plus.const import (
    CONF_AUTO_STOP,
    CONF_AUTO_STOP_DELAY,
    CONF_GRACE_PERIOD,
    CONF_INTERVAL,
    CONF_RUNNING_STATES,
    CONF_SOURCE_ENTITY,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType

DEFAULT_SOURCE_OPTIONS = {
    CONF_RUNNING_STATES: ["playing", "on"],
    CONF_GRACE_PERIOD: 120,
    CONF_AUTO_STOP: False,
    CONF_AUTO_STOP_DELAY: 1800,
}


def _duration(hours: int = 0, minutes: int = 0, seconds: int = 0) -> dict[str, int]:
    """Return a value as sent by the duration selector."""
    return {"hours": hours, "minutes": minutes, "seconds": seconds}


async def _start_user_flow(hass: HomeAssistant) -> dict[str, Any]:
    """Open the form for a new stopwatch."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
    return result


async def test_create_stopwatch(hass: HomeAssistant) -> None:
    """The user step creates an entry with the name as title and seconds as options."""
    result = await _start_user_flow(hass)
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
    assert result["options"] == {
        CONF_INTERVAL: 1815,
        CONF_UPDATE_INTERVAL: 60,
        **DEFAULT_SOURCE_OPTIONS,
    }
    assert hass.states.get("sensor.gaming_elapsed_time") is not None


async def test_create_stopwatch_with_source(hass: HomeAssistant) -> None:
    """The source section is flattened into the options."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"],
        {
            "name": "Gaming",
            CONF_INTERVAL: _duration(),
            CONF_UPDATE_INTERVAL: _duration(minutes=1),
            "source": {
                CONF_SOURCE_ENTITY: "media_player.xbox",
                CONF_RUNNING_STATES: ["playing", " gaming "],
                CONF_GRACE_PERIOD: _duration(minutes=5),
                CONF_AUTO_STOP: True,
                CONF_AUTO_STOP_DELAY: _duration(hours=1),
            },
        },
    )
    await hass.async_block_till_done()
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["options"] == {
        CONF_INTERVAL: 0,
        CONF_UPDATE_INTERVAL: 60,
        CONF_SOURCE_ENTITY: "media_player.xbox",
        CONF_RUNNING_STATES: ["playing", "gaming"],
        CONF_GRACE_PERIOD: 300,
        CONF_AUTO_STOP: True,
        CONF_AUTO_STOP_DELAY: 3600,
    }


async def test_invalid_durations_show_errors(hass: HomeAssistant) -> None:
    """Out-of-range durations are rejected with a message per field."""
    result = await _start_user_flow(hass)
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


@pytest.mark.parametrize(
    ("source", "error"),
    [
        (
            {CONF_SOURCE_ENTITY: "media_player.xbox", CONF_RUNNING_STATES: []},
            "running_states_required",
        ),
        ({CONF_GRACE_PERIOD: _duration(hours=2)}, "grace_period_too_long"),
        (
            {CONF_AUTO_STOP_DELAY: _duration(hours=7 * 24 + 1)},
            "auto_stop_delay_too_long",
        ),
    ],
)
async def test_invalid_source_settings_show_errors(
    hass: HomeAssistant, source: dict[str, Any], error: str
) -> None:
    """Invalid source settings are reported as a general error of the form."""
    result = await _start_user_flow(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"name": "Gaming", "source": source}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": error}


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
    assert setup_stopwatch.options == {
        CONF_INTERVAL: 45,
        CONF_UPDATE_INTERVAL: 10,
        **DEFAULT_SOURCE_OPTIONS,
    }
    assert setup_stopwatch.state is config_entries.ConfigEntryState.LOADED


@pytest.mark.parametrize(
    "options",
    [
        {
            CONF_INTERVAL: 0,
            CONF_UPDATE_INTERVAL: 60,
            CONF_SOURCE_ENTITY: "media_player.xbox",
            **DEFAULT_SOURCE_OPTIONS,
        }
    ],
)
async def test_options_keep_or_remove_source(
    hass: HomeAssistant, setup_stopwatch: MockConfigEntry
) -> None:
    """Without the source section the source is kept; a cleared field removes it."""
    result = await hass.config_entries.options.async_init(setup_stopwatch.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {CONF_INTERVAL: _duration(minutes=1)}
    )
    await hass.async_block_till_done()
    assert setup_stopwatch.options[CONF_SOURCE_ENTITY] == "media_player.xbox"
    assert setup_stopwatch.options[CONF_INTERVAL] == 60

    result = await hass.config_entries.options.async_init(setup_stopwatch.entry_id)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"source": {CONF_RUNNING_STATES: ["playing"]}}
    )
    await hass.async_block_till_done()
    assert CONF_SOURCE_ENTITY not in setup_stopwatch.options
    assert setup_stopwatch.options[CONF_RUNNING_STATES] == ["playing"]
