"""Enaro Home Assistant integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EnaroApiClient
from .const import (
    CONF_API_BASE_URL,
    CONF_EMAIL,
    CONF_PASSWORD,
    DATA_COORDINATOR,
    DATA_SENSOR_RULE_MANAGER,
    DOMAIN,
    PLATFORMS,
)
from .coordinator import EnaroShoppingCoordinator
from .sensor_rules import EnaroSensorRuleManager


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
    coordinator = EnaroShoppingCoordinator(hass, client)
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
