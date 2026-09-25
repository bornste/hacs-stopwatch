"""Sensors of the Stopwatch Plus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity
from homeassistant.const import UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import KEY_ELAPSED, KEY_LAST_SESSION, KEY_STATUS, STATUSES
from .entity import StopwatchEntity
from .stopwatch import format_duration

if TYPE_CHECKING:
    from . import StopwatchConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StopwatchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of a stopwatch."""
    stopwatch = entry.runtime_data
    async_add_entities(
        [
            StopwatchElapsedSensor(stopwatch, KEY_ELAPSED),
            StopwatchStatusSensor(stopwatch, KEY_STATUS),
            StopwatchLastSessionSensor(stopwatch, KEY_LAST_SESSION),
        ]
    )


class StopwatchSensor(StopwatchEntity, SensorEntity):
    """A sensor that follows the state of its stopwatch."""

    async def async_added_to_hass(self) -> None:
        """Subscribe to state changes of the stopwatch."""
        await super().async_added_to_hass()
        self.async_on_remove(
            self._stopwatch.async_add_listener(self.async_write_ha_state)
        )


class StopwatchElapsedSensor(StopwatchSensor):
    """The running time of a stopwatch."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    # Whole seconds; without this, Home Assistant would show two decimals
    _attr_suggested_display_precision = 0
    # Derived from the state, so it is not worth storing in the database
    _unrecorded_attributes = frozenset({"elapsed_formatted"})

    @property
    def native_value(self) -> int:
        """Return the running time in whole seconds."""
        return int(self._stopwatch.elapsed_seconds)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the formatted time and the values a card needs to count live."""
        stopwatch = self._stopwatch
        return {
            "elapsed_formatted": format_duration(stopwatch.elapsed_seconds),
            "status": stopwatch.status,
            "started_at": _isoformat(stopwatch.started_at),
            "running_since": _isoformat(stopwatch.running_since),
            "accumulated_seconds": round(stopwatch.accumulated_seconds, 3),
            "interval_count": stopwatch.interval_count,
        }


class StopwatchStatusSensor(StopwatchSensor):
    """The status of a stopwatch: idle, running or paused."""

    _attr_device_class = SensorDeviceClass.ENUM
    _attr_options = STATUSES

    @property
    def native_value(self) -> str:
        """Return the status."""
        return self._stopwatch.status


class StopwatchLastSessionSensor(StopwatchSensor):
    """The running time of the last session, set when the time goes back to zero."""

    _attr_device_class = SensorDeviceClass.DURATION
    _attr_native_unit_of_measurement = UnitOfTime.SECONDS
    _attr_suggested_display_precision = 0
    _unrecorded_attributes = frozenset({"elapsed_formatted"})

    @property
    def native_value(self) -> int | None:
        """Return the running time of the last session in whole seconds."""
        seconds = self._stopwatch.last_session_seconds
        return None if seconds is None else int(seconds)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return the formatted time and when the session ended."""
        stopwatch = self._stopwatch
        seconds = stopwatch.last_session_seconds
        return {
            "elapsed_formatted": None if seconds is None else format_duration(seconds),
            "ended_at": _isoformat(stopwatch.last_session_ended_at),
        }


def _isoformat(value: Any) -> str | None:
    """Convert an optional datetime to an ISO string."""
    return value.isoformat() if value else None
