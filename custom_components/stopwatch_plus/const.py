"""Constants for the Stopwatch Plus integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "stopwatch_plus"

# Config entry options, all in seconds
CONF_INTERVAL: Final = "interval"  # running time between interval events, 0 = off
CONF_UPDATE_INTERVAL: Final = "update_interval"

DEFAULT_INTERVAL: Final = 0
DEFAULT_UPDATE_INTERVAL: Final = 60
MAX_INTERVAL: Final = 24 * 3600
MIN_UPDATE_INTERVAL: Final = 1
MAX_UPDATE_INTERVAL: Final = 3600

# Optional source entity binding, durations in seconds
CONF_SOURCE_ENTITY: Final = "source_entity"
CONF_RUNNING_STATES: Final = "running_states"
CONF_GRACE_PERIOD: Final = "grace_period"
CONF_AUTO_RESET: Final = "auto_reset"
CONF_AUTO_RESET_DELAY: Final = "auto_reset_delay"

DEFAULT_RUNNING_STATES: Final = ["playing", "on"]
DEFAULT_GRACE_PERIOD: Final = 120
MAX_GRACE_PERIOD: Final = 3600
DEFAULT_AUTO_RESET: Final = False
DEFAULT_AUTO_RESET_DELAY: Final = 1800
MAX_AUTO_RESET_DELAY: Final = 7 * 24 * 3600

# Status of a stopwatch
STATUS_IDLE: Final = "idle"
STATUS_RUNNING: Final = "running"
STATUS_PAUSED: Final = "paused"
STATUSES: Final = [STATUS_IDLE, STATUS_RUNNING, STATUS_PAUSED]

# Event fired on the Home Assistant event bus
EVENT_STOPWATCH: Final = f"{DOMAIN}_event"

EVENT_TYPE_STARTED: Final = "started"
EVENT_TYPE_PAUSED: Final = "paused"
EVENT_TYPE_RESUMED: Final = "resumed"
EVENT_TYPE_RESET: Final = "reset"
EVENT_TYPE_INTERVAL: Final = "interval"
EVENT_TYPES: Final = [
    EVENT_TYPE_STARTED,
    EVENT_TYPE_PAUSED,
    EVENT_TYPE_RESUMED,
    EVENT_TYPE_RESET,
    EVENT_TYPE_INTERVAL,
]

# What caused a change
SOURCE_ACTION: Final = "action"
SOURCE_BUTTON: Final = "button"
SOURCE_SOURCE_ENTITY: Final = "source_entity"
SOURCE_AUTO_RESET: Final = "auto_reset"

# Actions
SERVICE_START: Final = "start"
SERVICE_PAUSE: Final = "pause"
SERVICE_RESET: Final = "reset"
SERVICE_TOGGLE: Final = "toggle"

# Unique id suffixes (also used as translation keys)
KEY_ELAPSED: Final = "elapsed"
KEY_STATUS: Final = "status"
KEY_START: Final = "start"
KEY_PAUSE: Final = "pause"
KEY_RESET: Final = "reset"
KEY_TOGGLE: Final = "toggle"
KEY_EVENTS: Final = "events"
