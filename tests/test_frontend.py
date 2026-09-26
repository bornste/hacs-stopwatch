"""Tests for serving the dashboard card."""

from __future__ import annotations

from unittest.mock import patch

from pytest_homeassistant_custom_component.typing import ClientSessionGenerator

from custom_components.stopwatch_plus.const import DOMAIN
from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component


async def test_card_is_served_and_loaded(
    hass: HomeAssistant, hass_client: ClientSessionGenerator
) -> None:
    """With the frontend, the card file is served and added as an extra module."""
    assert await async_setup_component(hass, "http", {})
    # The frontend itself needs the frontend package, so only its presence is simulated
    hass.config.components.add("frontend")
    with patch("custom_components.stopwatch_plus.frontend.add_extra_js_url") as add_url:
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    add_url.assert_called_once()
    url = add_url.call_args.args[1]
    assert url.startswith("/stopwatch_plus_frontend/stopwatch-plus-card.js?v=")

    client = await hass_client()
    response = await client.get(url)
    assert response.status == 200
    body = await response.text()
    assert "customElements.define(CARD_TYPE, StopwatchPlusCard)" in body

    # The card loads its texts from a second file next to it
    response = await client.get(url.replace("card.js", "card-translations.js"))
    assert response.status == 200
    assert "export const STRINGS" in await response.text()


async def test_no_card_without_frontend(hass: HomeAssistant) -> None:
    """Without the frontend (e.g. in a minimal setup), setup still works."""
    with patch("custom_components.stopwatch_plus.frontend.add_extra_js_url") as add_url:
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()
    add_url.assert_not_called()
