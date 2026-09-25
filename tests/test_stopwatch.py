"""Tests for the stopwatch logic, entities, actions and events."""

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
    CONF_INTERVAL,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
)
from custom_components.stopwatch_plus.sensor import StopwatchElapsedSensor
from custom_components.stopwatch_plus.stopwatch import format_duration
from homeassistant.core import Event, HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er

from .conftest import ELAPSED, PAUSE, RESET, START, STATUS, STOP

pytestmark = pytest.mark.usefixtures("setup_stopwatch")


async def _advance(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, seconds: float
) -> None:
    """Move the clock forward and run the scheduled callbacks."""
    freezer.tick(timedelta(seconds=seconds))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    """Press a button entity."""
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )


async def _action(hass: HomeAssistant, action: str, target: dict[str, Any]) -> None:
    """Call a Stopwatch Plus action."""
    await hass.services.async_call(DOMAIN, action, target=target, blocking=True)


def _elapsed(hass: HomeAssistant) -> int:
    """Return the state of the elapsed time sensor as a number."""
    return int(hass.states.get(ELAPSED).state)


async def test_initial_state(hass: HomeAssistant) -> None:
    """A new stopwatch is idle at zero."""
    elapsed = hass.states.get(ELAPSED)
    assert elapsed.state == "0"
    assert elapsed.attributes["device_class"] == "duration"
    assert elapsed.attributes["unit_of_measurement"] == "s"
    assert elapsed.attributes["status"] == "idle"
    assert hass.states.get(STATUS).state == "idle"
    for button in (START, PAUSE, STOP, RESET):
        assert hass.states.get(button) is not None


async def test_start_pause_resume_reset(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Pauses are not counted, reset goes back to idle at zero."""
    await _press(hass, START)
    assert hass.states.get(STATUS).state == "running"
    await _advance(hass, freezer, 90)
    await _press(hass, PAUSE)
    assert hass.states.get(STATUS).state == "paused"
    assert _elapsed(hass) == 90

    await _advance(hass, freezer, 300)
    assert _elapsed(hass) == 90

    await _press(hass, START)
    await _advance(hass, freezer, 30)
    await _press(hass, PAUSE)
    assert _elapsed(hass) == 120

    await _press(hass, RESET)
    assert hass.states.get(STATUS).state == "idle"
    assert _elapsed(hass) == 0

    assert [event.data["type"] for event in events] == [
        "started",
        "paused",
        "resumed",
        "paused",
        "reset",
    ]
    assert all(event.data["source"] == "button" for event in events)
    assert events[1].data["elapsed_seconds"] == 90
    assert events[1].data["elapsed_formatted"] == "00:01:30"
    assert events[1].data["entity_id"] == ELAPSED
    assert events[1].data["name"] == "Gaming"


async def test_commands_without_effect_fire_no_event(
    hass: HomeAssistant, events: list[Event]
) -> None:
    """Pausing or resetting an idle stopwatch and starting twice do nothing."""
    await _press(hass, PAUSE)
    await _press(hass, STOP)
    await _press(hass, RESET)
    await _press(hass, START)
    await _press(hass, START)
    assert [event.data["type"] for event in events] == ["started"]


async def test_sensor_updates_at_update_interval(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """While running, the sensor state only changes every update interval."""
    await _press(hass, START)
    await _advance(hass, freezer, 30)
    assert _elapsed(hass) == 0
    await _advance(hass, freezer, 30)
    assert _elapsed(hass) == 60


async def test_live_display_attributes(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The attributes allow a card to calculate the time itself."""
    await _press(hass, START)
    await _advance(hass, freezer, 45)
    await _press(hass, PAUSE)
    await _press(hass, START)
    attributes = hass.states.get(ELAPSED).attributes
    assert attributes["status"] == "running"
    assert attributes["accumulated_seconds"] == 45
    assert attributes["running_since"] is not None
    assert attributes["started_at"] is not None


async def test_actions_and_toggle(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """The actions work with an entity as target."""
    target = {"entity_id": ELAPSED}
    await _action(hass, "start", target)
    await _advance(hass, freezer, 10)
    await _action(hass, "toggle", target)
    assert hass.states.get(STATUS).state == "paused"
    await _action(hass, "toggle", target)
    assert hass.states.get(STATUS).state == "running"
    await _action(hass, "pause", target)
    await _action(hass, "reset", target)
    assert [event.data["type"] for event in events] == [
        "started",
        "paused",
        "resumed",
        "paused",
        "reset",
    ]
    assert all(event.data["source"] == "action" for event in events)


async def test_device_target_acts_once(
    hass: HomeAssistant, events: list[Event], setup_stopwatch: MockConfigEntry
) -> None:
    """Targeting the device (several entities) toggles the stopwatch only once."""
    device_id = er.async_get(hass).async_get(ELAPSED).device_id
    assert device_id is not None
    await _action(hass, "toggle", {"device_id": device_id})
    assert hass.states.get(STATUS).state == "running"
    assert len(events) == 1
    assert events[0].data["device_id"] == device_id


async def test_action_without_stopwatch_raises(hass: HomeAssistant) -> None:
    """An action whose target contains no stopwatch raises a clear error."""
    with pytest.raises(ServiceValidationError):
        await _action(hass, "start", {"entity_id": "sensor.does_not_exist"})


@pytest.mark.parametrize("options", [{CONF_INTERVAL: 60, CONF_UPDATE_INTERVAL: 60}])
async def test_interval_events_count_running_time_only(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Interval events fire per minute of running time; pauses do not count."""
    await _press(hass, START)
    await _advance(hass, freezer, 59)
    assert not [e for e in events if e.data["type"] == "interval"]
    await _advance(hass, freezer, 1)
    intervals = [e for e in events if e.data["type"] == "interval"]
    assert len(intervals) == 1
    assert intervals[0].data["elapsed_seconds"] == 60
    assert intervals[0].data["elapsed_formatted"] == "00:01:00"
    assert intervals[0].data["interval_count"] == 1
    assert intervals[0].data["source"] is None

    # 30 s running, then a long pause, then 30 s more running = 2 minutes
    await _advance(hass, freezer, 30)
    await _press(hass, PAUSE)
    await _advance(hass, freezer, 600)
    await _press(hass, START)
    await _advance(hass, freezer, 29)
    assert len([e for e in events if e.data["type"] == "interval"]) == 1
    await _advance(hass, freezer, 1)
    intervals = [e for e in events if e.data["type"] == "interval"]
    assert len(intervals) == 2
    assert intervals[1].data["elapsed_seconds"] == 120
    assert hass.states.get(ELAPSED).attributes["interval_count"] == 2


async def test_restore_running_counts_downtime(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_stopwatch: MockConfigEntry,
) -> None:
    """A running stopwatch keeps running across a restart, downtime included."""
    await _press(hass, START)
    await _advance(hass, freezer, 100)
    assert await hass.config_entries.async_unload(setup_stopwatch.entry_id)
    await hass.async_block_till_done()

    freezer.tick(timedelta(seconds=50))
    assert await hass.config_entries.async_setup(setup_stopwatch.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "running"
    assert _elapsed(hass) == 150


async def test_restore_paused_stays_paused(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    setup_stopwatch: MockConfigEntry,
) -> None:
    """A paused stopwatch is restored paused with its time."""
    await _press(hass, START)
    await _advance(hass, freezer, 40)
    await _press(hass, PAUSE)
    assert await hass.config_entries.async_unload(setup_stopwatch.entry_id)
    await hass.async_block_till_done()

    freezer.tick(timedelta(seconds=500))
    assert await hass.config_entries.async_setup(setup_stopwatch.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(STATUS).state == "paused"
    assert _elapsed(hass) == 40


@pytest.mark.parametrize("options", [{CONF_INTERVAL: 60, CONF_UPDATE_INTERVAL: 60}])
async def test_restore_skips_missed_intervals(
    hass: HomeAssistant,
    freezer: FrozenDateTimeFactory,
    events: list[Event],
    setup_stopwatch: MockConfigEntry,
) -> None:
    """Intervals missed during downtime are skipped, not fired in a burst."""
    await _press(hass, START)
    await _advance(hass, freezer, 30)
    assert await hass.config_entries.async_unload(setup_stopwatch.entry_id)
    await hass.async_block_till_done()

    # Down for 5 minutes: elapsed is now 5:30
    freezer.tick(timedelta(seconds=300))
    assert await hass.config_entries.async_setup(setup_stopwatch.entry_id)
    await hass.async_block_till_done()
    assert not [e for e in events if e.data["type"] == "interval"]

    # The next interval is at 6:00
    await _advance(hass, freezer, 30)
    intervals = [e for e in events if e.data["type"] == "interval"]
    assert len(intervals) == 1
    assert intervals[0].data["elapsed_seconds"] == 360
    assert intervals[0].data["interval_count"] == 6


@pytest.mark.parametrize("options", [{CONF_INTERVAL: 10, CONF_UPDATE_INTERVAL: 60}])
async def test_interval_shorter_than_update_interval(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Intervals fire on time even between sensor updates, and refresh the sensor."""
    await _press(hass, START)
    for expected in (10, 20, 30):
        await _advance(hass, freezer, 10)
        intervals = [e for e in events if e.data["type"] == "interval"]
        assert intervals[-1].data["elapsed_seconds"] == expected
        assert _elapsed(hass) == expected
    assert len([e for e in events if e.data["type"] == "interval"]) == 3


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00:00"),
        (150, "00:02:30"),
        (43509, "12:05:09"),
        (86399, "23:59:59"),
        (86400, "1.00:00:00"),
        (93784, "1.02:03:04"),
        (864005, "10.00:00:05"),
        (59.9, "00:00:59"),
    ],
)
def test_format_duration(seconds: float, expected: str) -> None:
    """Formatted like a .NET TimeSpan: HH:MM:SS, days only from 24 hours on."""
    assert format_duration(seconds) == expected


async def test_formatted_attribute_and_precision(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """The sensor has a formatted attribute (not recorded) and no decimals."""
    await _press(hass, START)
    await _advance(hass, freezer, 60)
    assert hass.states.get(ELAPSED).attributes["elapsed_formatted"] == "00:01:00"
    assert "elapsed_formatted" in StopwatchElapsedSensor._unrecorded_attributes
    options = er.async_get(hass).async_get(ELAPSED).options
    assert options["sensor"]["suggested_display_precision"] == 0


async def test_toggle_button(hass: HomeAssistant, events: list[Event]) -> None:
    """The Start/Pause button starts, pauses and resumes."""
    for expected in ("running", "paused", "running"):
        await _press(hass, "button.gaming_start_pause")
        assert hass.states.get(STATUS).state == expected
    assert [(e.data["type"], e.data["source"]) for e in events] == [
        ("started", "button"),
        ("paused", "button"),
        ("resumed", "button"),
    ]


async def test_stop_while_running(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Stop goes back to idle at zero, also while running."""
    await _press(hass, START)
    await _advance(hass, freezer, 60)
    await _press(hass, STOP)
    assert hass.states.get(STATUS).state == "idle"
    assert _elapsed(hass) == 0
    assert hass.states.get(ELAPSED).attributes["started_at"] is None
    assert events[-1].data["type"] == "stopped"
    assert events[-1].data["elapsed_seconds"] == 0

    # The next start is a new session
    await _press(hass, START)
    assert events[-1].data["type"] == "started"


@pytest.mark.parametrize("options", [{CONF_INTERVAL: 60, CONF_UPDATE_INTERVAL: 60}])
async def test_reset_while_running_keeps_running(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """Reset while running counts again from zero, intervals included."""
    await _press(hass, START)
    await _advance(hass, freezer, 90)
    await _press(hass, RESET)
    assert hass.states.get(STATUS).state == "running"
    assert _elapsed(hass) == 0
    assert hass.states.get(ELAPSED).attributes["interval_count"] == 0
    assert [e.data["type"] for e in events] == ["started", "interval", "reset"]

    # The next interval is one minute after the reset, not after the start
    await _advance(hass, freezer, 30)
    assert events[-1].data["type"] == "reset"
    await _advance(hass, freezer, 30)
    assert events[-1].data["type"] == "interval"
    assert events[-1].data["interval_count"] == 1
    assert _elapsed(hass) == 60


async def test_stop_and_reset_actions(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, events: list[Event]
) -> None:
    """The stop and reset actions work like the buttons."""
    target = {"entity_id": ELAPSED}
    await _action(hass, "start", target)
    await _advance(hass, freezer, 10)
    await _action(hass, "reset", target)
    assert hass.states.get(STATUS).state == "running"
    await _action(hass, "stop", target)
    assert hass.states.get(STATUS).state == "idle"
    assert [(e.data["type"], e.data["source"]) for e in events] == [
        ("started", "action"),
        ("reset", "action"),
        ("stopped", "action"),
    ]
