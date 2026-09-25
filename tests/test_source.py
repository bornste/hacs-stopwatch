"""Tests for the binding of a stopwatch to a source entity."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.stopwatch_plus.const import (
    CONF_AUTO_STOP,
    CONF_AUTO_STOP_DELAY,
    CONF_GRACE_PERIOD,
    CONF_INTERVAL,
    CONF_RUNNING_STATES,
    CONF_SOURCE_ENTITY,
    CONF_UPDATE_INTERVAL,
)
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, HomeAssistant

from .conftest import ELAPSED, LAST_SESSION, PAUSE, START, STATUS

XBOX = "media_player.xbox"


@pytest.fixture
def options() -> dict[str, Any]:
    """A stopwatch bound to the Xbox, with auto-stop after 30 minutes."""
    return {
        CONF_INTERVAL: 0,
        CONF_UPDATE_INTERVAL: 60,
        CONF_SOURCE_ENTITY: XBOX,
        CONF_RUNNING_STATES: ["playing"],
        CONF_GRACE_PERIOD: 120,
        CONF_AUTO_STOP: True,
        CONF_AUTO_STOP_DELAY: 1800,
    }


@pytest.fixture(autouse=True)
def xbox_off(hass: HomeAssistant) -> None:
    """The Xbox is off before the stopwatch is set up."""
    hass.states.async_set(XBOX, "off")


async def _advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float
) -> None:
    """Move the clock forward and run the scheduled callbacks."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _xbox(hass: HomeAssistant, state: str, **attributes: Any) -> None:
    """Set the state of the Xbox."""
    hass.states.async_set(XBOX, state, attributes)
    await hass.async_block_till_done()


def _elapsed(hass: HomeAssistant) -> float:
    """Return the exact elapsed time from the sensor attributes."""
    attributes = hass.states.get(ELAPSED).attributes
    return attributes["accumulated_seconds"]


def _types(events: list[Event]) -> list[tuple[str, str | None]]:
    """Return type and source of the collected events."""
    return [(event.data["type"], event.data["source"]) for event in events]


@pytest.mark.usefixtures("setup_stopwatch")
async def test_follows_the_source(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Playing starts and resumes, other states pause."""
    assert hass.states.get(STATUS).state == "idle"
    await _xbox(hass, "playing")
    assert hass.states.get(STATUS).state == "running"
    await _advance(hass, freezer, 100)
    await _xbox(hass, "idle")
    assert hass.states.get(STATUS).state == "paused"
    assert _elapsed(hass) == 100
    await _xbox(hass, "playing")
    assert _types(events) == [
        ("started", "source_entity"),
        ("paused", "source_entity"),
        ("resumed", "source_entity"),
    ]


@pytest.mark.usefixtures("setup_stopwatch")
async def test_same_meaning_changes_keep_a_manual_pause(
    hass: HomeAssistant, events: list[Event]
) -> None:
    """Attribute changes while playing do not resume a manually paused stopwatch."""
    await _xbox(hass, "playing", media_title="Game A")
    await hass.services.async_call(
        "button", "press", {"entity_id": PAUSE}, blocking=True
    )
    await _xbox(hass, "playing", media_title="Game B")
    assert hass.states.get(STATUS).state == "paused"
    # Manual buttons keep working while bound
    await hass.services.async_call(
        "button", "press", {"entity_id": START}, blocking=True
    )
    assert hass.states.get(STATUS).state == "running"


@pytest.mark.usefixtures("setup_stopwatch")
async def test_short_dropout_has_no_gap(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Unavailable for less than the grace period changes nothing."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 60)
    await _xbox(hass, STATE_UNAVAILABLE)
    await _advance(hass, freezer, 90)
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 150)
    assert hass.states.get(STATUS).state == "running"
    assert _types(events) == [("started", "source_entity")]
    await _xbox(hass, "off")
    assert _elapsed(hass) == 300


@pytest.mark.usefixtures("setup_stopwatch")
async def test_long_dropout_pauses_backdated(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """After the grace period, the unavailable time does not count."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 60)
    await _xbox(hass, STATE_UNAVAILABLE)
    await _advance(hass, freezer, 119)
    assert hass.states.get(STATUS).state == "running"
    await _advance(hass, freezer, 1)
    assert hass.states.get(STATUS).state == "paused"
    assert _elapsed(hass) == 60
    assert events[-1].data["type"] == "paused"
    assert events[-1].data["elapsed_seconds"] == 60


@pytest.mark.usefixtures("setup_stopwatch")
async def test_dropout_then_off_pauses_backdated(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Unavailable followed by a non-running state pauses from the dropout on."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 60)
    await _xbox(hass, STATE_UNAVAILABLE)
    await _advance(hass, freezer, 30)
    await _xbox(hass, "off")
    assert hass.states.get(STATUS).state == "paused"
    assert _elapsed(hass) == 60


@pytest.mark.usefixtures("setup_stopwatch")
async def test_auto_stop_after_the_delay(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Inactive for the delay: the session ends, the next start is a new one."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    await _advance(hass, freezer, 1799)
    assert hass.states.get(STATUS).state == "paused"
    await _advance(hass, freezer, 1)
    assert hass.states.get(STATUS).state == "idle"
    assert _elapsed(hass) == 0
    assert _types(events)[-1] == ("stopped", "auto_stop")
    # The event and the last session sensor keep the time of the session
    assert events[-1].data["elapsed_seconds"] == 600
    assert hass.states.get(LAST_SESSION).state == "600"

    await _xbox(hass, "playing")
    assert hass.states.get(STATUS).state == "running"
    assert _types(events)[-1] == ("started", "source_entity")


@pytest.mark.usefixtures("setup_stopwatch")
async def test_no_auto_stop_before_the_delay(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Back within the delay: the session continues."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    await _advance(hass, freezer, 1799)
    await _xbox(hass, "playing")
    assert _types(events)[-1] == ("resumed", "source_entity")
    assert _elapsed(hass) == 600

    # The delay starts again with the next inactivity
    await _xbox(hass, "off")
    await _advance(hass, freezer, 1799)
    assert hass.states.get(STATUS).state == "paused"
    await _advance(hass, freezer, 1)
    assert hass.states.get(STATUS).state == "idle"


@pytest.mark.usefixtures("setup_stopwatch")
async def test_no_auto_stop_of_a_manually_started_stopwatch(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """A stopwatch started by hand while the source is off keeps running."""
    await _xbox(hass, "playing")
    await _xbox(hass, "off")
    await _advance(hass, freezer, 60)
    await hass.services.async_call(
        "button", "press", {"entity_id": START}, blocking=True
    )
    await _advance(hass, freezer, 3600)
    assert "stopped" not in [event.data["type"] for event in events]
    assert hass.states.get(STATUS).state == "running"


@pytest.mark.usefixtures("setup_stopwatch")
async def test_auto_stop_while_the_source_is_unavailable(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """A source that turns off and then becomes unavailable still ends the session."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    await _advance(hass, freezer, 60)
    await _xbox(hass, STATE_UNAVAILABLE)
    await _advance(hass, freezer, 1740)
    assert hass.states.get(STATUS).state == "idle"
    assert _types(events)[-1] == ("stopped", "auto_stop")


@pytest.mark.usefixtures("setup_stopwatch")
async def test_auto_stop_after_a_long_dropout(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """The delay of a dropout counts from its start, like the backdated pause."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, STATE_UNAVAILABLE)
    await _advance(hass, freezer, 120)
    assert hass.states.get(STATUS).state == "paused"
    await _advance(hass, freezer, 1680)
    assert hass.states.get(STATUS).state == "idle"
    assert events[-1].data["elapsed_seconds"] == 600


@pytest.mark.usefixtures("setup_stopwatch")
@pytest.mark.parametrize(
    "options",
    [
        {
            CONF_INTERVAL: 0,
            CONF_UPDATE_INTERVAL: 60,
            CONF_SOURCE_ENTITY: XBOX,
            CONF_RUNNING_STATES: ["playing"],
            CONF_GRACE_PERIOD: 120,
            CONF_AUTO_STOP: False,
            CONF_AUTO_STOP_DELAY: 1800,
        }
    ],
)
async def test_no_auto_stop_when_turned_off(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Without auto-stop, the stopwatch stays paused."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    await _advance(hass, freezer, 7200)
    assert hass.states.get(STATUS).state == "paused"
    assert _elapsed(hass) == 600


async def test_starts_when_the_source_already_plays(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """At setup the stopwatch follows the current state of the source."""
    await _xbox(hass, "playing")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "running"


async def test_auto_stop_across_a_restart(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_stopwatch: MockConfigEntry,
    events: list[Event],
) -> None:
    """A delay that ran out while Home Assistant was down stops right after start."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    assert await hass.config_entries.async_unload(setup_stopwatch.entry_id)
    await hass.async_block_till_done()

    freezer.tick(timedelta(hours=8))
    assert await hass.config_entries.async_setup(setup_stopwatch.entry_id)
    await _advance(hass, freezer, 0)
    assert hass.states.get(STATUS).state == "idle"
    assert _types(events)[-1] == ("stopped", "auto_stop")
    assert hass.states.get(LAST_SESSION).state == "600"


async def test_auto_stop_delay_continues_across_a_restart(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_stopwatch: MockConfigEntry,
) -> None:
    """A restart within the delay keeps the original deadline."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    assert await hass.config_entries.async_unload(setup_stopwatch.entry_id)
    await hass.async_block_till_done()

    freezer.tick(timedelta(minutes=20))
    assert await hass.config_entries.async_setup(setup_stopwatch.entry_id)
    await _advance(hass, freezer, 0)
    assert hass.states.get(STATUS).state == "paused"
    await _advance(hass, freezer, 600)
    assert hass.states.get(STATUS).state == "idle"


async def test_grace_period_continues_across_a_restart(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_stopwatch: MockConfigEntry,
) -> None:
    """A dropout that started before a restart keeps its original grace period."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 60)
    await _xbox(hass, STATE_UNAVAILABLE)
    await _advance(hass, freezer, 60)
    assert await hass.config_entries.async_unload(setup_stopwatch.entry_id)
    await hass.async_block_till_done()

    freezer.tick(timedelta(seconds=30))
    assert await hass.config_entries.async_setup(setup_stopwatch.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "running"
    await _advance(hass, freezer, 30)
    assert hass.states.get(STATUS).state == "paused"
    assert _elapsed(hass) == 60


@pytest.mark.usefixtures("setup_stopwatch")
@pytest.mark.parametrize(
    "options",
    [
        {
            CONF_INTERVAL: 0,
            CONF_UPDATE_INTERVAL: 60,
            CONF_SOURCE_ENTITY: XBOX,
            CONF_RUNNING_STATES: ["playing"],
            CONF_GRACE_PERIOD: 0,
            CONF_AUTO_STOP: False,
            CONF_AUTO_STOP_DELAY: 1800,
        }
    ],
)
async def test_no_grace_period_pauses_immediately(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """With a grace period of 0, unavailable pauses right away like any other state."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 60)
    await _xbox(hass, STATE_UNAVAILABLE)
    await _advance(hass, freezer, 0)
    assert hass.states.get(STATUS).state == "paused"
    assert _elapsed(hass) == 60
    await _xbox(hass, "playing")
    assert _types(events)[-2:] == [
        ("paused", "source_entity"),
        ("resumed", "source_entity"),
    ]


@pytest.mark.usefixtures("setup_stopwatch")
@pytest.mark.parametrize(
    "options",
    [
        {
            CONF_INTERVAL: 0,
            CONF_UPDATE_INTERVAL: 60,
            CONF_SOURCE_ENTITY: XBOX,
            CONF_RUNNING_STATES: ["playing"],
            CONF_GRACE_PERIOD: 120,
            CONF_AUTO_STOP: True,
            CONF_AUTO_STOP_DELAY: 0,
        }
    ],
)
async def test_auto_stop_delay_zero_stops_right_away(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """With a delay of 0, the session ends as soon as the source is inactive."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 300)
    await _xbox(hass, "off")
    await _advance(hass, freezer, 0)
    assert hass.states.get(STATUS).state == "idle"
    assert _types(events)[-2:] == [
        ("paused", "source_entity"),
        ("stopped", "auto_stop"),
    ]
    assert events[-1].data["elapsed_seconds"] == 300
    await _xbox(hass, "playing")
    assert _types(events)[-1] == ("started", "source_entity")

    # A manual pause while the source keeps playing is not stopped
    await hass.services.async_call(
        "button", "press", {"entity_id": PAUSE}, blocking=True
    )
    await _advance(hass, freezer, 60)
    assert hass.states.get(STATUS).state == "paused"
    await hass.services.async_call(
        "button", "press", {"entity_id": START}, blocking=True
    )
    assert _types(events)[-1] == ("resumed", "button")
