"""Buttons of the Stopwatch Plus integration."""

from __future__ import annotations

from typing import TYPE_CHECKING

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import KEY_PAUSE, KEY_RESET, KEY_START, SOURCE_BUTTON
from .entity import StopwatchEntity

if TYPE_CHECKING:
    from . import StopwatchConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: StopwatchConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the buttons of a stopwatch."""
    stopwatch = entry.runtime_data
    async_add_entities(
        [
            StopwatchStartButton(stopwatch, KEY_START),
            StopwatchPauseButton(stopwatch, KEY_PAUSE),
            StopwatchResetButton(stopwatch, KEY_RESET),
        ]
    )


class StopwatchStartButton(StopwatchEntity, ButtonEntity):
    """Starts or resumes the stopwatch."""

    async def async_press(self) -> None:
        """Handle the button press."""
        self._stopwatch.async_start(SOURCE_BUTTON)


class StopwatchPauseButton(StopwatchEntity, ButtonEntity):
    """Pauses the stopwatch."""

    async def async_press(self) -> None:
        """Handle the button press."""
        self._stopwatch.async_pause(SOURCE_BUTTON)


class StopwatchResetButton(StopwatchEntity, ButtonEntity):
    """Resets the stopwatch."""

    async def async_press(self) -> None:
        """Handle the button press."""
        self._stopwatch.async_reset(SOURCE_BUTTON)
