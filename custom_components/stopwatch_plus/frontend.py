"""Serve the dashboard card and load it on every dashboard."""

from __future__ import annotations

import logging
from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant
from homeassistant.loader import async_get_integration

from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

URL_BASE = f"/{DOMAIN}_frontend"
CARD_FILE = "stopwatch-plus-card.js"


async def async_setup_frontend(hass: HomeAssistant) -> None:
    """Register the card file and add it to the modules the frontend loads."""
    if "http" not in hass.config.components or "frontend" not in hass.config.components:
        _LOGGER.debug("Frontend not loaded, the dashboard card is not registered")
        return

    card_dir = str(Path(__file__).parent / "www")
    await hass.http.async_register_static_paths(
        [StaticPathConfig(URL_BASE, card_dir, cache_headers=False)]
    )
    # The version in the URL makes browsers load the new file after an update
    integration = await async_get_integration(hass, DOMAIN)
    add_extra_js_url(hass, f"{URL_BASE}/{CARD_FILE}?v={integration.version}")
