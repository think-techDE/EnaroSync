"""Switch platform for Enaro sensor rules."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.util import slugify

from .const import (
    CONF_RULE_ENABLED,
    CONF_RULE_ENTITY_ID,
    CONF_RULE_ID,
    CONF_RULE_TARGET_STATE,
    CONF_SENSOR_RULES,
    DATA_SENSOR_RULE_MANAGER,
    DOMAIN,
)
from .sensor_rules import EnaroSensorRuleManager, sensor_rule_signal, sensor_rules_from_options


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enaro sensor rule switch entities."""
    manager: EnaroSensorRuleManager = hass.data[DOMAIN][entry.entry_id][
        DATA_SENSOR_RULE_MANAGER
    ]
    async_add_entities(
        EnaroSensorRuleSwitchEntity(hass, entry, manager, rule)
        for rule in sensor_rules_from_options(entry.options)
    )


class EnaroSensorRuleSwitchEntity(SwitchEntity):
    """Enable or disable one Enaro sensor rule."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_has_entity_name = True
    _attr_icon = "mdi:toggle-switch-outline"

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
        self._attr_name = f"Sensorregel {entity_name}"
        self._attr_unique_id = f"{DOMAIN}_{entry.entry_id}_sensor_rule_{self._rule_id}_enabled"
        self.entity_id = f"switch.enaro_sensorregel_{slugify(entity_name)}"

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
    def is_on(self) -> bool:
        """Return if the rule is enabled."""
        return bool(self._rule.get(CONF_RULE_ENABLED, True))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return rule details."""
        return {
            "watched_entity_id": self._rule.get(CONF_RULE_ENTITY_ID),
            "target_state": self._rule.get(CONF_RULE_TARGET_STATE),
            "incident_active": bool(self._manager.rule_state(self._rule_id).get("incident_active")),
            "task_created": bool(self._manager.rule_state(self._rule_id).get("task_created")),
        }

    @property
    def device_info(self) -> dict[str, Any]:
        """Return Home Assistant device info."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": "Enaro Integration",
            "manufacturer": "Think-Tech",
            "model": "Enaro Home Assistant Integration",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        """Enable the rule."""
        await self._async_set_enabled(True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        """Disable the rule."""
        await self._async_set_enabled(False)

    async def _async_set_enabled(self, enabled: bool) -> None:
        options = dict(self._entry.options)
        updated_rules: list[dict[str, Any]] = []
        for rule in sensor_rules_from_options(options):
            updated_rule = dict(rule)
            if updated_rule.get(CONF_RULE_ID) == self._rule_id:
                updated_rule[CONF_RULE_ENABLED] = enabled
            updated_rules.append(updated_rule)
        options[CONF_SENSOR_RULES] = updated_rules
        self.hass.config_entries.async_update_entry(self._entry, options=options)
        await self.hass.config_entries.async_reload(self._entry.entry_id)


def _friendly_entity_name(hass: HomeAssistant, rule: dict[str, Any]) -> str:
    entity_id = str(rule.get(CONF_RULE_ENTITY_ID) or "Sensor")
    if (state := hass.states.get(entity_id)) is not None:
        return state.name or entity_id
    return entity_id