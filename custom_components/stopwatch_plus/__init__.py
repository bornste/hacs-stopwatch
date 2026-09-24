"""The Stopwatch Plus integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a stopwatch from a config entry."""
    # Platforms and the stopwatch state logic follow in the next milestone.
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a stopwatch config entry."""
    return True
