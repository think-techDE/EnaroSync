"""Sensor platform for Enaro sensor rules."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    CONF_RULE_ALIAS,
    CONF_RULE_ENABLED,
    CONF_RULE_ENTITY_ID,
    CONF_RULE_HOUSEHOLD_ID,
    CONF_RULE_ID,
    CONF_RULE_IMPORTANT,
    CONF_RULE_MEMBER_ID,
    CONF_RULE_NOTES_TEMPLATE,
    CONF_RULE_TARGET_STATE,
    CONF_RULE_TITLE_TEMPLATE,
    DATA_SENSOR_RULE_MANAGER,
    DOMAIN,
)
from .sensor_rules import EnaroSensorRuleManager, sensor_rule_signal, sensor_rules_from_options


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enaro sensor rule status entities."""
    manager: EnaroSensorRuleManager = hass.data[DOMAIN][entry.entry_id][
        DATA_SENSOR_RULE_MANAGER
    ]
    async_add_entities(
        EnaroSensorRuleStatusEntity(hass, entry, manager, rule)
        for rule in sensor_rules_from_options(entry.options)
    )


class EnaroSensorRuleStatusEntity(SensorEntity):
    """Read-only status entity for one Enaro sensor rule."""

    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_has_entity_name = True

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        manager: EnaroSensorRuleManager,
        rule: dict[str, Any],
    ) -> None:
        self.hass = hass
        self._entry = entry
        self._manager = manager
        self._rule = rule
        self._rule_id = str(rule[CONF_RULE_ID])
        entity_name = _friendly_entity_name(hass, rule)
        self._attr_name = f"{entity_name} Status"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_sensor_rule_{self._rule_id}_status"
        self.entity_id = f"sensor.enaro_sensorregel_{slugify(entity_name)}"

    async def async_added_to_hass(self) -> None:
        """Register dispatcher updates from the rule manager."""
        self.async_on_remove(
            async_dispatcher_connect(
                self.hass,
                sensor_rule_signal(self._entry.entry_id),
                self.async_write_ha_state,
            )
        )

    @property
    def native_value(self) -> str:
        """Return current rule status."""
        if not self._enabled:
            return "deaktiviert"
        state = self._runtime_state
        if state.get("task_created"):
            return "aufgabe_erstellt"
        if state.get("incident_active"):
            return "wartet"
        return "bereit"

    @property
    def icon(self) -> str:
        """Return status icon."""
        if not self._enabled:
            return "mdi:toggle-switch-off-outline"
        state = self._runtime_state
        if state.get("task_created"):
            return "mdi:clipboard-check-outline"
        if state.get("incident_active"):
            return "mdi:alert-circle-outline"
        return "mdi:shield-check-outline"

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return detailed rule information for Home Assistant."""
        watched = self.hass.states.get(str(self._rule[CONF_RULE_ENTITY_ID]))
        runtime = self._runtime_state
        return {
            "enabled": self._enabled,
            "alias": self._rule.get(CONF_RULE_ALIAS),
            "watched_entity_id": self._rule.get(CONF_RULE_ENTITY_ID),
            "watched_entity_name": watched.name if watched is not None else None,
            "current_state": watched.state if watched is not None else None,
            "target_state": self._rule.get(CONF_RULE_TARGET_STATE),
            "important": bool(self._rule.get(CONF_RULE_IMPORTANT)),
            "household_id": self._rule.get(CONF_RULE_HOUSEHOLD_ID),
            "member_id": self._rule.get(CONF_RULE_MEMBER_ID),
            "title_template": self._rule.get(CONF_RULE_TITLE_TEMPLATE),
            "notes_template": self._rule.get(CONF_RULE_NOTES_TEMPLATE),
            "incident_active": bool(runtime.get("incident_active")),
            "task_created": bool(runtime.get("task_created")),
            "active_task_id": runtime.get("active_task_id"),
            "last_task_created_at": runtime.get("last_task_created_at"),
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return Home Assistant device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Enaro Integration",
            "manufacturer": "Think-Tech",
            "model": "Enaro Home Assistant Integration",
            "sw_version": "0.2.7",
            "configuration_url": "https://github.com/think-techDE/EnaroSync",
        }

    @property
    def _enabled(self) -> bool:
        return bool(self._rule.get(CONF_RULE_ENABLED, True))

    @property
    def _runtime_state(self) -> dict[str, Any]:
        return self._manager.rule_state(self._rule_id)


def _friendly_entity_name(hass: HomeAssistant, rule: dict[str, Any]) -> str:
    if alias := str(rule.get(CONF_RULE_ALIAS) or "").strip():
        return alias
    entity_id = str(rule.get(CONF_RULE_ENTITY_ID) or "Sensor")
    if (state := hass.states.get(entity_id)) is not None:
        return state.name or entity_id
    return entity_id
