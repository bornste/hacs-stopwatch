"""Tests for the device triggers."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import async_get_device_automations

from custom_components.stopwatch_plus.const import DOMAIN
from homeassistant.components.device_automation import DeviceAutomationType
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component

from .conftest import ELAPSED, PAUSE, START

pytestmark = pytest.mark.usefixtures("setup_stopwatch")

TRIGGER_TYPES = [
    "started",
    "paused",
    "resumed",
    "stopped",
    "reset",
    "interval",
]


def _device_id(hass: HomeAssistant) -> str:
    """Return the device of the test stopwatch."""
    device_id = er.async_get(hass).async_get(ELAPSED).device_id
    assert device_id is not None
    return device_id


async def test_get_triggers(hass: HomeAssistant) -> None:
    """The device offers one trigger per event type."""
    device_id = _device_id(hass)
    triggers = await async_get_device_automations(
        hass, DeviceAutomationType.TRIGGER, device_id
    )
    # The sensors and buttons of the device add their own entity triggers
    own = [trigger for trigger in triggers if trigger["domain"] == DOMAIN]
    assert sorted(trigger["type"] for trigger in own) == sorted(TRIGGER_TYPES)
    assert all(trigger["device_id"] == device_id for trigger in own)


async def test_trigger_fires_with_event_data(hass: HomeAssistant) -> None:
    """An automation with a device trigger runs with the stopwatch event data."""
    device_id = _device_id(hass)
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": [
                {
                    "triggers": {
                        "trigger": "device",
                        "domain": DOMAIN,
                        "device_id": device_id,
                        "type": trigger_type,
                    },
                    "actions": {
                        "event": "test_trigger_fired",
                        "event_data": {
                            "trigger_type": trigger_type,
                            "event_type": "{{ trigger.event.data.type }}",
                            "elapsed": "{{ trigger.event.data.elapsed_formatted }}",
                        },
                    },
                }
                for trigger_type in ("started", "paused")
            ]
        },
    )
    fired: list[dict[str, Any]] = []

    @callback
    def listener(event: Event) -> None:
        fired.append(dict(event.data))

    hass.bus.async_listen("test_trigger_fired", listener)

    for button in (START, PAUSE):
        await hass.services.async_call(
            "button", "press", {"entity_id": button}, blocking=True
        )
    await hass.async_block_till_done()

    assert fired == [
        {"trigger_type": "started", "event_type": "started", "elapsed": "00:00:00"},
        {"trigger_type": "paused", "event_type": "paused", "elapsed": "00:00:00"},
    ]


async def test_invalid_trigger_type_is_rejected(hass: HomeAssistant) -> None:
    """An unknown trigger type does not set up the automation."""
    assert await async_setup_component(
        hass,
        "automation",
        {
            "automation": {
                "alias": "broken",
                "triggers": {
                    "trigger": "device",
                    "domain": DOMAIN,
                    "device_id": _device_id(hass),
                    "type": "exploded",
                },
                "actions": {"event": "never"},
            }
        },
    )
    await hass.async_block_till_done()
    state = hass.states.get("automation.broken")
    assert state is None or state.state == "unavailable"
