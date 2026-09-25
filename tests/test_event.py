"""Tests for the event entity and the entity-based trigger "Event received"."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from freezegun.api import FrozenDateTimeFactory
import pytest
from pytest_homeassistant_custom_component.common import async_fire_time_changed

from custom_components.stopwatch_plus.const import CONF_INTERVAL, CONF_UPDATE_INTERVAL
from homeassistant.components import automation
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .conftest import ELAPSED, PAUSE, RESET, START

EVENTS = "event.gaming_events"

pytestmark = pytest.mark.usefixtures("setup_stopwatch")

# Before the entity-based triggers were released, they were a Labs preview feature
requires_entity_triggers = pytest.mark.skipif(
    hasattr(automation, "NEW_TRIGGERS_CONDITIONS_FEATURE_FLAG"),
    reason="Entity-based triggers are a Labs preview in this Home Assistant version",
)


async def _press(hass: HomeAssistant, entity_id: str) -> None:
    """Press a button entity."""
    await hass.services.async_call(
        "button", "press", {"entity_id": entity_id}, blocking=True
    )


async def test_event_entity(hass: HomeAssistant) -> None:
    """The stopwatch has an event entity on its device with all event types."""
    state = hass.states.get(EVENTS)
    assert state is not None
    assert state.attributes["event_types"] == [
        "started",
        "paused",
        "resumed",
        "reset",
        "interval",
    ]
    registry = er.async_get(hass)
    assert registry.async_get(EVENTS).device_id == registry.async_get(ELAPSED).device_id


async def test_reports_every_event(hass: HomeAssistant) -> None:
    """Each command is reported with the event data as attributes."""
    reported: list[str] = []
    for button in (START, PAUSE, START, RESET):
        await _press(hass, button)
        reported.append(hass.states.get(EVENTS).attributes["event_type"])
    assert reported == ["started", "paused", "resumed", "reset"]

    attributes = hass.states.get(EVENTS).attributes
    assert attributes["source"] == "button"
    assert attributes["elapsed_formatted"] == "00:00:00"
    assert "device_id" not in attributes


@pytest.mark.parametrize("options", [{CONF_INTERVAL: 60, CONF_UPDATE_INTERVAL: 60}])
async def test_reports_interval(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    """Interval events are reported with the exact elapsed time."""
    await _press(hass, START)
    freezer.tick(timedelta(seconds=60))
    async_fire_time_changed(hass)
    await hass.async_block_till_done()
    attributes = hass.states.get(EVENTS).attributes
    assert attributes["event_type"] == "interval"
    assert attributes["elapsed_formatted"] == "00:01:00"
    assert attributes["interval_count"] == 1


@requires_entity_triggers
async def test_event_received_trigger(hass: HomeAssistant) -> None:
    """The trigger "Event received" works with the stopwatch as target."""
    device_id = er.async_get(hass).async_get(EVENTS).device_id
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "triggers": {
                    "trigger": "event.received",
                    "target": {"device_id": device_id},
                    "options": {"event_type": ["paused"]},
                },
                "actions": {
                    "event": "test_trigger_fired",
                    "event_data": {
                        "event_type": "{{ trigger.to_state.attributes.event_type }}",
                        "elapsed": (
                            "{{ trigger.to_state.attributes.elapsed_formatted }}"
                        ),
                    },
                },
            }
        },
    )
    fired: list[dict[str, Any]] = []

    @callback
    def listener(event: Event) -> None:
        fired.append(dict(event.data))

    hass.bus.async_listen("test_trigger_fired", listener)

    await _press(hass, START)
    await _press(hass, PAUSE)
    await hass.async_block_till_done()
    assert fired == [{"event_type": "paused", "elapsed": "00:00:00"}]
