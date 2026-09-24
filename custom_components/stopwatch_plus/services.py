"""Actions of the Stopwatch Plus integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, callback
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_registry as er
from homeassistant.helpers.service import async_extract_entity_ids

from .const import (
    DOMAIN,
    SERVICE_PAUSE,
    SERVICE_RESET,
    SERVICE_START,
    SERVICE_TOGGLE,
    SOURCE_ACTION,
)
from .stopwatch import Stopwatch

SERVICE_SCHEMA = cv.make_entity_service_schema({})


async def _async_get_stopwatches(call: ServiceCall) -> list[Stopwatch]:
    """Return each targeted stopwatch once, even if several of its entities match."""
    hass = call.hass
    entity_registry = er.async_get(hass)
    entry_ids: set[str] = set()
    for entity_id in await async_extract_entity_ids(call):
        entity_entry = entity_registry.async_get(entity_id)
        if (
            entity_entry is not None
            and entity_entry.platform == DOMAIN
            and entity_entry.config_entry_id is not None
        ):
            entry_ids.add(entity_entry.config_entry_id)

    stopwatches: list[Stopwatch] = []
    for entry_id in entry_ids:
        entry = hass.config_entries.async_get_entry(entry_id)
        if entry is not None and entry.state is ConfigEntryState.LOADED:
            stopwatches.append(entry.runtime_data)

    if not stopwatches:
        raise ServiceValidationError(
            translation_domain=DOMAIN, translation_key="no_stopwatch_targeted"
        )
    return stopwatches


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Register the actions."""

    async def async_start(call: ServiceCall) -> None:
        for stopwatch in await _async_get_stopwatches(call):
            stopwatch.async_start(SOURCE_ACTION)

    async def async_pause(call: ServiceCall) -> None:
        for stopwatch in await _async_get_stopwatches(call):
            stopwatch.async_pause(SOURCE_ACTION)

    async def async_reset(call: ServiceCall) -> None:
        for stopwatch in await _async_get_stopwatches(call):
            stopwatch.async_reset(SOURCE_ACTION)

    async def async_toggle(call: ServiceCall) -> None:
        for stopwatch in await _async_get_stopwatches(call):
            stopwatch.async_toggle(SOURCE_ACTION)

    for name, handler in (
        (SERVICE_START, async_start),
        (SERVICE_PAUSE, async_pause),
        (SERVICE_RESET, async_reset),
        (SERVICE_TOGGLE, async_toggle),
    ):
        hass.services.async_register(DOMAIN, name, handler, schema=SERVICE_SCHEMA)
