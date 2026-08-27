"""Enaro Home Assistant integration."""

from __future__ import annotations

from pathlib import Path

import voluptuous as vol
from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.components.todo import DOMAIN as TODO_DOMAIN
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv, service
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import EnaroApiClient
from .const import (
    CONF_API_BASE_URL,
    CONF_EMAIL,
    CONF_PASSWORD,
    DATA_COORDINATOR,
    DATA_SENSOR_RULE_MANAGER,
    DATA_WALLBOARD_CARD_REGISTERED,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EnaroShoppingCoordinator
from .sensor_rules import EnaroSensorRuleManager


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Register integration-wide entity services."""
    service.async_register_platform_entity_service(
        hass,
        DOMAIN,
        "snooze_task",
        entity_domain=TODO_DOMAIN,
        schema={
            vol.Required("uid"): cv.string,
            vol.Required("preset"): vol.In(["tomorrow", "week"]),
        },
        func="async_snooze_task",
    )
    return True


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Set up Enaro Integration from a config entry."""
    client = EnaroApiClient(
        session=async_get_clientsession(hass),
        api_base_url=entry.data[CONF_API_BASE_URL],
        email=entry.data[CONF_EMAIL],
        password=entry.data[CONF_PASSWORD],
    )
    coordinator = EnaroShoppingCoordinator(hass, client, entry.entry_id)
    await coordinator.async_load_wallboard_cache()
    await coordinator.async_config_entry_first_refresh()
    sensor_rule_manager = EnaroSensorRuleManager(hass, entry, client)
    await sensor_rule_manager.async_setup()

    hass.config_entries.async_update_entry(
        entry,
        title=f"Enaro Integration ({entry.data[CONF_EMAIL]})",
    )

    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        DATA_COORDINATOR: coordinator,
        DATA_SENSOR_RULE_MANAGER: sensor_rule_manager,
    }
    await _async_register_wallboard_card(hass)
    entry.async_on_unload(entry.add_update_listener(_async_update_listener))
    await hass.config_entries.async_forward_entry_setups(
        entry,
        [Platform(platform) for platform in PLATFORMS],
    )
    return True


async def async_unload_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> bool:
    """Unload Enaro Integration."""
    unload_ok = await hass.config_entries.async_unload_platforms(
        entry,
        [Platform(platform) for platform in PLATFORMS],
    )
    if unload_ok:
        data = hass.data[DOMAIN].pop(entry.entry_id)
        await data[DATA_SENSOR_RULE_MANAGER].async_unload()
    return unload_ok


async def _async_update_listener(
    hass: HomeAssistant,
    entry: ConfigEntry,
) -> None:
    """Reload the integration when options change."""
    await hass.config_entries.async_reload(entry.entry_id)


async def _async_register_wallboard_card(hass: HomeAssistant) -> None:
    """Serve and register the bundled wallboard card once per HA runtime."""
    domain_data = hass.data.setdefault(DOMAIN, {})
    if domain_data.get(DATA_WALLBOARD_CARD_REGISTERED):
        return
    card_path = Path(__file__).parent / "www" / "enaro-wallboard-card.js"
    await hass.http.async_register_static_paths(
        [
            StaticPathConfig(
                "/enaro_shopping/enaro-wallboard-card.js",
                str(card_path),
                False,
            )
        ]
    )
    add_extra_js_url(
        hass,
        "/enaro_shopping/enaro-wallboard-card.js?v=0.3.0",
    )
    domain_data[DATA_WALLBOARD_CARD_REGISTERED] = True
