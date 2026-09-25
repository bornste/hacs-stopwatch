"""The Stopwatch Plus integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.typing import ConfigType

from .const import (
    CONF_AUTO_STOP,
    CONF_AUTO_STOP_DELAY,
    CONF_GRACE_PERIOD,
    CONF_INTERVAL,
    CONF_RUNNING_STATES,
    CONF_SOURCE_ENTITY,
    CONF_UPDATE_INTERVAL,
    DEFAULT_AUTO_STOP,
    DEFAULT_AUTO_STOP_DELAY,
    DEFAULT_GRACE_PERIOD,
    DEFAULT_INTERVAL,
    DEFAULT_RUNNING_STATES,
    DEFAULT_UPDATE_INTERVAL,
    DOMAIN,
)
from .frontend import async_setup_frontend
from .services import async_setup_services
from .source import SourceBinding
from .stopwatch import Stopwatch

PLATFORMS: list[Platform] = [Platform.BUTTON, Platform.EVENT, Platform.SENSOR]

CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)

type StopwatchConfigEntry = ConfigEntry[Stopwatch]


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Set up the actions and the dashboard card of the integration."""
    async_setup_services(hass)
    await async_setup_frontend(hass)
    return True


async def async_setup_entry(hass: HomeAssistant, entry: StopwatchConfigEntry) -> bool:
    """Set up a stopwatch from a config entry."""
    stopwatch = Stopwatch(
        hass,
        entry.entry_id,
        entry.title,
        interval_seconds=int(entry.options.get(CONF_INTERVAL, DEFAULT_INTERVAL)),
        update_interval_seconds=int(
            entry.options.get(CONF_UPDATE_INTERVAL, DEFAULT_UPDATE_INTERVAL)
        ),
    )
    await stopwatch.async_load()
    entry.runtime_data = stopwatch

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Started after the entities exist, so its events can name them
    if source_entity := entry.options.get(CONF_SOURCE_ENTITY):
        options = entry.options
        binding = SourceBinding(
            hass,
            stopwatch,
            source_entity,
            running_states=list(
                options.get(CONF_RUNNING_STATES, DEFAULT_RUNNING_STATES)
            ),
            grace_period_seconds=int(
                options.get(CONF_GRACE_PERIOD, DEFAULT_GRACE_PERIOD)
            ),
            auto_stop=bool(options.get(CONF_AUTO_STOP, DEFAULT_AUTO_STOP)),
            auto_stop_delay_seconds=int(
                options.get(CONF_AUTO_STOP_DELAY, DEFAULT_AUTO_STOP_DELAY)
            ),
        )
        stopwatch.async_on_shutdown(binding.async_stop)
        binding.async_start()
    else:
        # A source removed in the options leaves no stale binding data behind
        stopwatch.source_data.clear()
    return True


async def async_unload_entry(hass: HomeAssistant, entry: StopwatchConfigEntry) -> bool:
    """Unload a stopwatch config entry."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        await entry.runtime_data.async_shutdown()
    return unloaded


async def async_remove_entry(hass: HomeAssistant, entry: StopwatchConfigEntry) -> None:
    """Delete the saved state when a stopwatch is removed."""
    await Stopwatch.async_remove_storage(hass, entry.entry_id)
