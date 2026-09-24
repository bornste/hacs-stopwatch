"""Base entity of the Stopwatch Plus integration."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity

from .const import DOMAIN
from .stopwatch import Stopwatch


class StopwatchEntity(Entity):
    """An entity that belongs to a stopwatch device."""

    _attr_has_entity_name = True
    _attr_should_poll = False

    def __init__(self, stopwatch: Stopwatch, key: str) -> None:
        """Initialize the entity."""
        self._stopwatch = stopwatch
        self._attr_unique_id = f"{stopwatch.entry_id}_{key}"
        self._attr_translation_key = key
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, stopwatch.entry_id)},
            name=stopwatch.name,
            entry_type=DeviceEntryType.SERVICE,
        )
