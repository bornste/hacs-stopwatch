"""State logic of a single stopwatch."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timedelta
import logging
from typing import Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_time_interval,
)
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    EVENT_STOPWATCH,
    EVENT_TYPE_INTERVAL,
    EVENT_TYPE_PAUSED,
    EVENT_TYPE_RESET,
    EVENT_TYPE_RESUMED,
    EVENT_TYPE_STARTED,
    KEY_ELAPSED,
    STATUS_IDLE,
    STATUS_PAUSED,
    STATUS_RUNNING,
    STATUSES,
)

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1
SAVE_DELAY = 1  # seconds


def format_duration(seconds: float) -> str:
    """Format seconds as HH:MM:SS, with days as d.HH:MM:SS from 24 hours on.

    Same as the constant ("c") format of a .NET TimeSpan, e.g. 00:02:30 or 1.02:03:04.
    """
    days, rest = divmod(int(seconds), 86400)
    hours, rest = divmod(rest, 3600)
    minutes, secs = divmod(rest, 60)
    formatted = f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{days}.{formatted}" if days else formatted


def _storage_key(entry_id: str) -> str:
    """Return the storage key of a stopwatch."""
    return f"{DOMAIN}.{entry_id}"


class Stopwatch:
    """A stopwatch that counts running time and can be paused and resumed.

    The elapsed time is kept as the running time accumulated up to the last
    start (accumulated_seconds) plus the time since that start (running_since).
    This keeps the state exact without having to tick every second.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        name: str,
        interval_seconds: int,
        update_interval_seconds: int,
    ) -> None:
        """Initialize the stopwatch."""
        self.hass = hass
        self.entry_id = entry_id
        self.name = name
        self._interval_seconds = interval_seconds
        self._update_interval = timedelta(seconds=update_interval_seconds)
        self._store: Store[dict[str, Any]] = Store(
            hass, STORAGE_VERSION, _storage_key(entry_id)
        )

        self.status: str = STATUS_IDLE
        self.accumulated_seconds: float = 0.0
        self.running_since: datetime | None = None
        self.started_at: datetime | None = None
        self.interval_count: int = 0

        self._listeners: list[CALLBACK_TYPE] = []
        self._cancel_interval: CALLBACK_TYPE | None = None
        self._cancel_update: CALLBACK_TYPE | None = None

    @property
    def elapsed_seconds(self) -> float:
        """Return the running time in seconds."""
        if self.running_since is None:
            return self.accumulated_seconds
        return (
            self.accumulated_seconds
            + (dt_util.utcnow() - self.running_since).total_seconds()
        )

    # Persistence

    async def async_load(self) -> None:
        """Restore the state saved before the last shutdown."""
        data = await self._store.async_load()
        if not data or data.get("status") not in STATUSES:
            return

        self.status = data["status"]
        self.accumulated_seconds = float(data.get("accumulated_seconds", 0.0))
        self.running_since = dt_util.parse_datetime(data.get("running_since") or "")
        self.started_at = dt_util.parse_datetime(data.get("started_at") or "")
        self.interval_count = int(data.get("interval_count", 0))

        if self.status == STATUS_RUNNING and self.running_since is None:
            # Inconsistent data, keep the counted time but stop counting
            self.status = STATUS_PAUSED
        if self.status != STATUS_RUNNING:
            self.running_since = None

        if self._interval_seconds:
            # Intervals missed while Home Assistant was down are skipped,
            # so a restart does not cause a burst of announcements.
            self.interval_count = max(
                self.interval_count,
                int(self.elapsed_seconds // self._interval_seconds),
            )

        self._schedule()

    async def async_shutdown(self) -> None:
        """Stop all timers and save the state immediately."""
        self._unschedule()
        await self._store.async_save(self._as_dict())

    @staticmethod
    async def async_remove_storage(hass: HomeAssistant, entry_id: str) -> None:
        """Delete the saved state of a removed stopwatch."""
        await Store(hass, STORAGE_VERSION, _storage_key(entry_id)).async_remove()

    def _as_dict(self) -> dict[str, Any]:
        """Return the state as a dictionary for storage."""
        return {
            "status": self.status,
            "accumulated_seconds": self.accumulated_seconds,
            "running_since": _isoformat(self.running_since),
            "started_at": _isoformat(self.started_at),
            "interval_count": self.interval_count,
        }

    # Listeners

    @callback
    def async_add_listener(self, update_callback: CALLBACK_TYPE) -> Callable[[], None]:
        """Register a callback that is called whenever the state changes."""
        self._listeners.append(update_callback)

        @callback
        def remove_listener() -> None:
            self._listeners.remove(update_callback)

        return remove_listener

    @callback
    def _notify(self) -> None:
        """Inform all listeners (the entities) about a change."""
        for update_callback in list(self._listeners):
            update_callback()

    @callback
    def _changed(self) -> None:
        """Save the state and inform the listeners."""
        self._store.async_delay_save(self._as_dict, SAVE_DELAY)
        self._notify()

    # Commands

    @callback
    def async_start(self, source: str) -> None:
        """Start the stopwatch, or resume it when it is paused."""
        if self.status == STATUS_RUNNING:
            return

        now = dt_util.utcnow()
        if self.status == STATUS_IDLE:
            event_type = EVENT_TYPE_STARTED
            self.started_at = now
            self.accumulated_seconds = 0.0
            self.interval_count = 0
        else:
            event_type = EVENT_TYPE_RESUMED

        self.status = STATUS_RUNNING
        self.running_since = now
        self._schedule()
        self._changed()
        self._fire_event(event_type, source)

    @callback
    def async_pause(self, source: str) -> None:
        """Pause the stopwatch."""
        if self.status != STATUS_RUNNING:
            return

        self.accumulated_seconds = self.elapsed_seconds
        self.running_since = None
        self.status = STATUS_PAUSED
        self._unschedule()
        self._changed()
        self._fire_event(EVENT_TYPE_PAUSED, source)

    @callback
    def async_reset(self, source: str) -> None:
        """Reset the stopwatch to zero and stop it."""
        if self.status == STATUS_IDLE:
            return

        self.status = STATUS_IDLE
        self.accumulated_seconds = 0.0
        self.running_since = None
        self.started_at = None
        self.interval_count = 0
        self._unschedule()
        self._changed()
        self._fire_event(EVENT_TYPE_RESET, source)

    @callback
    def async_toggle(self, source: str) -> None:
        """Pause the stopwatch when it is running, otherwise start it."""
        if self.status == STATUS_RUNNING:
            self.async_pause(source)
        else:
            self.async_start(source)

    # Timers

    @callback
    def _schedule(self) -> None:
        """Schedule the sensor updates and the next interval while running."""
        self._unschedule()
        if self.status != STATUS_RUNNING or self.running_since is None:
            return

        self._cancel_update = async_track_time_interval(
            self.hass, self._handle_update_tick, self._update_interval
        )

        if self._interval_seconds:
            next_threshold = (self.interval_count + 1) * self._interval_seconds
            fire_at = self.running_since + timedelta(
                seconds=next_threshold - self.accumulated_seconds
            )
            self._cancel_interval = async_track_point_in_utc_time(
                self.hass, self._handle_interval, fire_at
            )

    @callback
    def _unschedule(self) -> None:
        """Cancel all scheduled callbacks."""
        if self._cancel_update is not None:
            self._cancel_update()
            self._cancel_update = None
        if self._cancel_interval is not None:
            self._cancel_interval()
            self._cancel_interval = None

    @callback
    def _handle_update_tick(self, _now: datetime) -> None:
        """Refresh the sensors while running."""
        self._notify()

    @callback
    def _handle_interval(self, _now: datetime) -> None:
        """Fire the interval event and schedule the next one."""
        self._cancel_interval = None
        self.interval_count += 1
        # Report the exact threshold instead of the slightly later firing time
        self._fire_event(
            EVENT_TYPE_INTERVAL,
            None,
            elapsed_seconds=self.interval_count * self._interval_seconds,
        )
        self._schedule()
        self._changed()

    # Events

    @callback
    def _fire_event(
        self,
        event_type: str,
        source: str | None,
        elapsed_seconds: float | None = None,
    ) -> None:
        """Fire a stopwatch event on the event bus."""
        if elapsed_seconds is None:
            elapsed_seconds = self.elapsed_seconds

        entity_registry = er.async_get(self.hass)
        entity_id = entity_registry.async_get_entity_id(
            "sensor", DOMAIN, f"{self.entry_id}_{KEY_ELAPSED}"
        )
        # The device is looked up via the sensor, which works on all supported versions
        entity_entry = entity_registry.async_get(entity_id) if entity_id else None

        data = {
            "type": event_type,
            "entity_id": entity_id,
            "device_id": entity_entry.device_id if entity_entry else None,
            "name": self.name,
            "elapsed_seconds": int(elapsed_seconds),
            "elapsed_formatted": format_duration(elapsed_seconds),
            "interval_count": self.interval_count,
            "source": source,
        }
        _LOGGER.debug("Firing %s: %s", EVENT_STOPWATCH, data)
        self.hass.bus.async_fire(EVENT_STOPWATCH, data)


def _isoformat(value: datetime | None) -> str | None:
    """Convert an optional datetime to an ISO string."""
    return value.isoformat() if value else None
