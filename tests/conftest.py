"""Shared fixtures for the Stopwatch Plus tests."""

from __future__ import annotations

from typing import Any

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.stopwatch_plus.const import (
    CONF_INTERVAL,
    CONF_UPDATE_INTERVAL,
    DOMAIN,
    EVENT_STOPWATCH,
)
from homeassistant.core import Event, HomeAssistant, callback

ELAPSED = "sensor.gaming_elapsed_time"
STATUS = "sensor.gaming_status"
START = "button.gaming_start"
PAUSE = "button.gaming_pause"
RESET = "button.gaming_reset"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow loading the integration from custom_components in every test."""


@pytest.fixture
def options() -> dict[str, Any]:
    """Options of the test stopwatch; tests can override this fixture."""
    return {CONF_INTERVAL: 0, CONF_UPDATE_INTERVAL: 60}


@pytest.fixture
def config_entry(options: dict[str, Any]) -> MockConfigEntry:
    """A config entry for a stopwatch called "Gaming"."""
    return MockConfigEntry(domain=DOMAIN, title="Gaming", data={}, options=options)


@pytest.fixture
async def setup_stopwatch(
    hass: HomeAssistant, config_entry: MockConfigEntry
) -> MockConfigEntry:
    """Set up the test stopwatch."""
    config_entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry


@pytest.fixture
def events(hass: HomeAssistant) -> list[Event]:
    """Collect all stopwatch events."""
    collected: list[Event] = []

    @callback
    def listener(event: Event) -> None:
        collected.append(event)

    hass.bus.async_listen(EVENT_STOPWATCH, listener)
    return collected
