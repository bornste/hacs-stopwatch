"""Event entity of the Stopwatch Plus integration.

Every stopwatch event is also reported by an event entity. Home Assistant's
entity-based trigger "Event received" can then be used in the automation editor
with the stopwatch as target.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.event import EventEntity
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import EVENT_TYPES, KEY_EVENTS
from .entity import StopwatchEntity

if TYPE_CHECKING:
    from . import StopwatchConfigEntry

PARALLEL_UPDATES = 0

# Event data that is not repeated as attribute: it identifies this entity anyway
_OMITTED_EVENT_DATA = frozenset({"type", "entity_id", "device_id", "name"})


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StopwatchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the event entity of a stopwatch."""
    async_add_entities([StopwatchEventEntity(entry.runtime_data, KEY_EVENTS)])


class StopwatchEventEntity(StopwatchEntity, EventEntity):
    """Reports started, paused, resumed, reset and interval events."""

    _attr_event_types = EVENT_TYPES

    async def async_added_to_hass(self) -> None:
        """Subscribe to the events of the stopwatch."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._stopwatch.async_add_event_listener(self._handle_stopwatch_event)
        )

    @callback
    def _handle_stopwatch_event(self, data: dict[str, Any]) -> None:
        """Report a stopwatch event with its data as attributes."""
        attributes = {
            key: value for key, value in data.items() if key not in _OMITTED_EVENT_DATA
        }
        self._trigger_event(data["type"], attributes)
        self.async_write_ha_state()
