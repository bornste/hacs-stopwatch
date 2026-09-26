"""Binding of a stopwatch to a source entity (e.g. a TV or a window sensor)."""

from __future__ import annotations

from datetime import datetime, timedelta
from enum import Enum
import logging

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import (
    CALLBACK_TYPE,
    Event,
    EventStateChangedData,
    HomeAssistant,
    State,
    callback,
)
from homeassistant.helpers.event import (
    async_track_point_in_utc_time,
    async_track_state_change_event,
)
from homeassistant.util import dt as dt_util

from .const import SOURCE_AUTO_STOP, SOURCE_SOURCE_ENTITY, STATUS_PAUSED
from .stopwatch import Stopwatch

_LOGGER = logging.getLogger(__name__)

# Keys in Stopwatch.source_data, persisted across restarts
KEY_INACTIVE_SINCE = "inactive_since"
KEY_UNAVAILABLE_SINCE = "unavailable_since"


class SourceState(Enum):
    """How a state of the source entity is interpreted."""

    RUNNING = "running"
    INACTIVE = "inactive"
    UNAVAILABLE = "unavailable"


class SourceBinding:
    """Start, pause and stop a stopwatch following a source entity.

    - A "running" state starts or resumes the stopwatch.
    - Any other valid state pauses it.
    - unavailable/unknown keeps the stopwatch as it is for a grace period. If the
      source does not come back as running within it, the stopwatch is paused,
      backdated to the moment the source became unavailable.
    - With auto-stop, a source that stays inactive for the delay ends the
      session: the stopwatch is stopped (back to zero), so the next start of the
      source begins a new session.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        stopwatch: Stopwatch,
        entity_id: str,
        running_states: list[str],
        grace_period_seconds: int,
        auto_stop: bool,
        auto_stop_delay_seconds: int,
    ) -> None:
        """Initialize the binding."""
        self.hass = hass
        self._stopwatch = stopwatch
        self._entity_id = entity_id
        self._running_states = {state.strip() for state in running_states}
        self._grace_period = timedelta(seconds=grace_period_seconds)
        self._auto_stop = auto_stop
        self._auto_stop_delay = timedelta(seconds=auto_stop_delay_seconds)
        self._cancel_state_listener: CALLBACK_TYPE | None = None
        self._cancel_grace_timer: CALLBACK_TYPE | None = None
        self._cancel_stop_timer: CALLBACK_TYPE | None = None
        self._stop_deadline: datetime | None = None

    @callback
    def async_start(self) -> None:
        """Follow the source entity, beginning with its current state."""
        self._cancel_state_listener = async_track_state_change_event(
            self.hass, [self._entity_id], self._handle_state_change
        )
        # After a restart, a persisted unavailable_since keeps the original
        # grace period running
        self._apply(self.hass.states.get(self._entity_id), dt_util.utcnow())

    @callback
    def async_stop(self) -> None:
        """Stop following the source entity."""
        if self._cancel_state_listener is not None:
            self._cancel_state_listener()
            self._cancel_state_listener = None
        self._cancel_grace()
        self._cancel_auto_stop()

    def _classify(self, state: State | None) -> SourceState:
        """Interpret a state of the source entity."""
        if state is None or state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return SourceState.UNAVAILABLE
        if state.state in self._running_states:
            return SourceState.RUNNING
        return SourceState.INACTIVE

    @callback
    def _handle_state_change(self, event: Event[EventStateChangedData]) -> None:
        """React when the source changes between running, inactive and unavailable.

        Changes that keep the same meaning (e.g. only attributes changed, or
        playing -> on) are ignored, so a manual pause is not undone by them.
        """
        old_state, new_state = event.data["old_state"], event.data["new_state"]
        if self._classify(old_state) is self._classify(new_state):
            return
        self._apply(new_state, dt_util.utcnow())

    @callback
    def _apply(self, state: State | None, now: datetime) -> None:
        """Bring the stopwatch in line with the source state."""
        source_state = self._classify(state)
        _LOGGER.debug(
            "%s: source %s is %s", self._stopwatch.name, self._entity_id, source_state
        )
        if source_state is SourceState.RUNNING:
            self._on_running(now)
        elif source_state is SourceState.INACTIVE:
            self._on_inactive(now)
        else:
            self._on_unavailable(now)
        self._update_auto_stop()

    @callback
    def _on_running(self, now: datetime) -> None:
        """Start or resume the stopwatch."""
        self._cancel_grace()
        self._set_time(KEY_UNAVAILABLE_SINCE, None)
        self._set_time(KEY_INACTIVE_SINCE, None)
        self._stopwatch.async_start(SOURCE_SOURCE_ENTITY)

    @callback
    def _on_inactive(self, now: datetime) -> None:
        """Pause, backdated if the source was unavailable before."""
        self._cancel_grace()
        unavailable_since = self._get_time(KEY_UNAVAILABLE_SINCE)
        self._set_time(KEY_UNAVAILABLE_SINCE, None)
        self._stopwatch.async_pause(SOURCE_SOURCE_ENTITY, at=unavailable_since)
        if self._get_time(KEY_INACTIVE_SINCE) is None:
            self._set_time(KEY_INACTIVE_SINCE, unavailable_since or now)

    @callback
    def _on_unavailable(self, now: datetime) -> None:
        """Keep the stopwatch as it is and start the grace period."""
        if self._cancel_grace_timer is not None:
            return
        unavailable_since = self._get_time(KEY_UNAVAILABLE_SINCE)
        if unavailable_since is None:
            unavailable_since = now
            self._set_time(KEY_UNAVAILABLE_SINCE, unavailable_since)
        self._schedule_grace_timer(unavailable_since)

    @callback
    def _schedule_grace_timer(self, unavailable_since: datetime) -> None:
        """Pause the stopwatch when the grace period is over."""
        self._cancel_grace()
        self._cancel_grace_timer = async_track_point_in_utc_time(
            self.hass,
            self._handle_grace_expired,
            unavailable_since + self._grace_period,
        )

    @callback
    def _handle_grace_expired(self, now: datetime) -> None:
        """The source stayed unavailable too long: pause, backdated."""
        self._cancel_grace_timer = None
        unavailable_since = self._get_time(KEY_UNAVAILABLE_SINCE) or now
        self._stopwatch.async_pause(SOURCE_SOURCE_ENTITY, at=unavailable_since)
        if self._get_time(KEY_INACTIVE_SINCE) is None:
            self._set_time(KEY_INACTIVE_SINCE, unavailable_since)
        self._update_auto_stop()

    @callback
    def _update_auto_stop(self) -> None:
        """Schedule the automatic stop while the source is inactive.

        The stop is due when the source has been inactive for the delay. It only
        applies to a paused stopwatch, so a stopwatch started by hand in the
        meantime keeps running. A deadline that passed while Home Assistant was
        down stops the stopwatch right after the start.
        """
        inactive_since = self._get_time(KEY_INACTIVE_SINCE)
        if (
            not self._auto_stop
            or inactive_since is None
            or self._stopwatch.status != STATUS_PAUSED
        ):
            self._cancel_auto_stop()
            return
        deadline = inactive_since + self._auto_stop_delay
        if self._cancel_stop_timer is not None and self._stop_deadline == deadline:
            return
        self._cancel_auto_stop()
        self._stop_deadline = deadline
        self._cancel_stop_timer = async_track_point_in_utc_time(
            self.hass, self._handle_auto_stop, max(deadline, dt_util.utcnow())
        )

    @callback
    def _handle_auto_stop(self, _now: datetime) -> None:
        """The source stayed inactive for the delay: end the session."""
        self._cancel_stop_timer = None
        self._stop_deadline = None
        if (
            self._get_time(KEY_INACTIVE_SINCE) is not None
            and self._stopwatch.status == STATUS_PAUSED
        ):
            self._stopwatch.async_stop(SOURCE_AUTO_STOP)

    @callback
    def _cancel_auto_stop(self) -> None:
        """Cancel a scheduled automatic stop."""
        if self._cancel_stop_timer is not None:
            self._cancel_stop_timer()
            self._cancel_stop_timer = None
        self._stop_deadline = None

    @callback
    def _cancel_grace(self) -> None:
        """Cancel a running grace period."""
        if self._cancel_grace_timer is not None:
            self._cancel_grace_timer()
            self._cancel_grace_timer = None

    def _get_time(self, key: str) -> datetime | None:
        """Read a persisted point in time."""
        value = self._stopwatch.source_data.get(key)
        return dt_util.parse_datetime(value) if value else None

    @callback
    def _set_time(self, key: str, value: datetime | None) -> None:
        """Persist a point in time."""
        new_value = value.isoformat() if value else None
        if self._stopwatch.source_data.get(key) != new_value:
            self._stopwatch.source_data[key] = new_value
            self._stopwatch.async_request_save()
