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
    CONF_AUTO_RESET,
    CONF_AUTO_RESET_DELAY,
    CONF_GRACE_PERIOD,
    CONF_INTERVAL,
    CONF_RUNNING_STATES,
    CONF_SOURCE_ENTITY,
    CONF_UPDATE_INTERVAL,
)
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import Event, HomeAssistant

from .conftest import ELAPSED, PAUSE, START, STATUS

XBOX = "media_player.xbox"


@pytest.fixture
def options() -> dict[str, Any]:
    """A stopwatch bound to the Xbox, with auto-reset after 30 minutes."""
    return {
        CONF_INTERVAL: 0,
        CONF_UPDATE_INTERVAL: 60,
        CONF_SOURCE_ENTITY: XBOX,
        CONF_RUNNING_STATES: ["playing"],
        CONF_GRACE_PERIOD: 120,
        CONF_AUTO_RESET: True,
        CONF_AUTO_RESET_DELAY: 1800,
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
async def test_auto_reset_after_the_delay(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Inactive for at least the delay: the next start is a new session."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    await _advance(hass, freezer, 1800)
    # The last session stays visible until the next start
    assert _elapsed(hass) == 600
    await _xbox(hass, "playing")
    assert hass.states.get(STATUS).state == "running"
    assert _elapsed(hass) == 0
    assert _types(events)[-2:] == [
        ("reset", "auto_reset"),
        ("started", "source_entity"),
    ]


@pytest.mark.usefixtures("setup_stopwatch")
async def test_no_auto_reset_before_the_delay(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Inactive for less than the delay: the session continues."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    await _advance(hass, freezer, 1799)
    await _xbox(hass, "playing")
    assert _types(events)[-1] == ("resumed", "source_entity")
    assert _elapsed(hass) == 600


@pytest.mark.usefixtures("setup_stopwatch")
async def test_no_auto_reset_of_a_manually_started_stopwatch(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """A stopwatch started by hand while the source was off is not reset."""
    await _xbox(hass, "playing")
    await _xbox(hass, "off")
    await _advance(hass, freezer, 3600)
    await hass.services.async_call(
        "button", "press", {"entity_id": START}, blocking=True
    )
    await _advance(hass, freezer, 60)
    await _xbox(hass, "playing")
    assert "reset" not in [event.data["type"] for event in events]
    assert hass.states.get(STATUS).state == "running"


async def test_starts_when_the_source_already_plays(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> None:
    """At setup the stopwatch follows the current state of the source."""
    await _xbox(hass, "playing")
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "running"


async def test_auto_reset_across_a_restart(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_stopwatch: MockConfigEntry,
    events: list[Event],
) -> None:
    """The inactivity time survives a restart of Home Assistant."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 600)
    await _xbox(hass, "off")
    assert await hass.config_entries.async_unload(setup_stopwatch.entry_id)
    await hass.async_block_till_done()

    freezer.tick(timedelta(hours=8))
    assert await hass.config_entries.async_setup(setup_stopwatch.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "paused"
    await _xbox(hass, "playing")
    assert _types(events)[-2:] == [
        ("reset", "auto_reset"),
        ("started", "source_entity"),
    ]


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
            CONF_AUTO_RESET: False,
            CONF_AUTO_RESET_DELAY: 1800,
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
            CONF_AUTO_RESET: True,
            CONF_AUTO_RESET_DELAY: 0,
        }
    ],
)
async def test_auto_reset_delay_zero_resets_on_every_start(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """With a delay of 0, every new start of the source is a new session."""
    await _xbox(hass, "playing")
    await _advance(hass, freezer, 300)
    await _xbox(hass, "off")
    assert _elapsed(hass) == 300
    await _xbox(hass, "playing")
    assert _elapsed(hass) == 0
    assert _types(events)[-2:] == [
        ("reset", "auto_reset"),
        ("started", "source_entity"),
    ]

    # A manual pause while the source keeps playing is resumed without a reset
    await hass.services.async_call(
        "button", "press", {"entity_id": PAUSE}, blocking=True
    )
    await hass.services.async_call(
        "button", "press", {"entity_id": START}, blocking=True
    )
    assert _types(events)[-1] == ("resumed", "button")
