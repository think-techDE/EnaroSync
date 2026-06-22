"""Sensor rules that create Enaro tasks from Home Assistant states."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import Event, HomeAssistant, State, callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.event import async_call_later, async_track_state_change_event
from homeassistant.helpers.storage import Store

from .api import EnaroApiClient, EnaroApiError
from .const import (
    CONF_RULE_ENABLED,
    CONF_RULE_ENTITY_ID,
    CONF_RULE_HOUSEHOLD_ID,
    CONF_RULE_ID,
    CONF_RULE_IMPORTANT,
    CONF_RULE_MEMBER_ID,
    CONF_RULE_NOTES_TEMPLATE,
    CONF_RULE_TARGET_STATE,
    CONF_RULE_TITLE_TEMPLATE,
    CONF_SENSOR_RULES,
    DEFAULT_SENSOR_RULE_NOTES_TEMPLATE,
    DEFAULT_SENSOR_RULE_TITLE_TEMPLATE,
    DOMAIN,
    SENSOR_RULE_DEBOUNCE_SECONDS,
    SENSOR_RULE_RETRY_SECONDS,
)

LOGGER = logging.getLogger(__name__)
STORAGE_VERSION = 1


class EnaroSensorRuleManager:
    """Watch configured Home Assistant states and create Enaro tasks."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: EnaroApiClient,
    ) -> None:
        self.hass = hass
        self.entry = entry
        self.client = client
        self._store = Store(
            hass,
            STORAGE_VERSION,
            f"{DOMAIN}_sensor_rules_{entry.entry_id}",
        )
        self._rule_states: dict[str, dict[str, Any]] = {}
        self._timer_unsubs: dict[str, CALLBACK_TYPE] = {}
        self._state_unsub: CALLBACK_TYPE | None = None

    async def async_setup(self) -> None:
        """Set up state listeners for configured rules."""
        stored = await self._store.async_load()
        if isinstance(stored, dict):
            self._rule_states = {
                str(rule_id): dict(rule_state)
                for rule_id, rule_state in stored.get("rules", {}).items()
                if isinstance(rule_state, dict)
            }

        rules = _configured_rules(self.entry.options)
        self._initialize_rule_states(rules)
        await self._async_save()

        entity_ids = sorted({rule[CONF_RULE_ENTITY_ID] for rule in rules})
        if entity_ids:
            self._state_unsub = async_track_state_change_event(
                self.hass,
                entity_ids,
                self._handle_state_change,
            )

    async def async_unload(self) -> None:
        """Unload state listeners and pending timers."""
        if self._state_unsub is not None:
            self._state_unsub()
            self._state_unsub = None
        for unsubscribe in self._timer_unsubs.values():
            unsubscribe()
        self._timer_unsubs.clear()
        await self._async_save()

    @callback
    def _handle_state_change(self, event: Event) -> None:
        self.hass.async_create_task(self._async_handle_state_change(event))

    async def _async_handle_state_change(self, event: Event) -> None:
        entity_id = event.data.get("entity_id")
        old_state = event.data.get("old_state")
        new_state = event.data.get("new_state")
        if not isinstance(entity_id, str) or not isinstance(new_state, State):
            return

        for rule in _configured_rules(self.entry.options):
            if rule[CONF_RULE_ENTITY_ID] != entity_id:
                continue
            old_matches = isinstance(old_state, State) and _state_matches(
                old_state,
                rule,
            )
            new_matches = _state_matches(new_state, rule)
            if new_matches and not old_matches:
                await self._async_enter_target_state(rule)
            elif old_matches and not new_matches:
                await self._async_leave_target_state(rule)

    async def _async_enter_target_state(self, rule: dict[str, Any]) -> None:
        rule_id = rule[CONF_RULE_ID]
        rule_state = self._rule_states.setdefault(rule_id, {})
        if rule_state.get("incident_active"):
            return
        rule_state.update(
            {
                "incident_active": True,
                "task_created": False,
                "active_task_id": None,
            }
        )
        await self._async_save()
        self._schedule_rule(rule_id, SENSOR_RULE_DEBOUNCE_SECONDS)

    async def _async_leave_target_state(self, rule: dict[str, Any]) -> None:
        rule_id = rule[CONF_RULE_ID]
        self._cancel_timer(rule_id)
        rule_state = self._rule_states.setdefault(rule_id, {})
        rule_state.update(
            {
                "incident_active": False,
                "task_created": False,
                "active_task_id": None,
            }
        )
        await self._async_save()

    def _schedule_rule(self, rule_id: str, delay: int) -> None:
        self._cancel_timer(rule_id)

        @callback
        def _fire(_now: datetime) -> None:
            self._timer_unsubs.pop(rule_id, None)
            self.hass.async_create_task(self._async_fire_rule(rule_id))

        self._timer_unsubs[rule_id] = async_call_later(self.hass, delay, _fire)

    def _cancel_timer(self, rule_id: str) -> None:
        unsubscribe = self._timer_unsubs.pop(rule_id, None)
        if unsubscribe is not None:
            unsubscribe()

    async def _async_fire_rule(self, rule_id: str) -> None:
        rule = _rule_by_id(_configured_rules(self.entry.options), rule_id)
        if rule is None:
            return

        state = self.hass.states.get(rule[CONF_RULE_ENTITY_ID])
        rule_state = self._rule_states.setdefault(rule_id, {})
        if (
            state is None
            or not _state_matches(state, rule)
            or not rule_state.get("incident_active")
            or rule_state.get("task_created")
        ):
            return

        triggered_at = datetime.now(UTC)
        try:
            task = await self.client.async_create_task(
                rule[CONF_RULE_HOUSEHOLD_ID],
                title=_render_template(
                    rule.get(CONF_RULE_TITLE_TEMPLATE)
                    or DEFAULT_SENSOR_RULE_TITLE_TEMPLATE,
                    state,
                    triggered_at,
                    fallback=state.name or state.entity_id,
                ),
                notes=_render_template(
                    rule.get(CONF_RULE_NOTES_TEMPLATE)
                    or DEFAULT_SENSOR_RULE_NOTES_TEMPLATE,
                    state,
                    triggered_at,
                    fallback="",
                )
                or None,
                assigned_member_ids=[rule[CONF_RULE_MEMBER_ID]],
                important=bool(rule.get(CONF_RULE_IMPORTANT)),
                due_at=triggered_at,
            )
        except (ConfigEntryAuthFailed, EnaroApiError) as err:
            LOGGER.warning(
                "Could not create Enaro task for sensor rule %s: %s",
                rule_id,
                err,
            )
            if _state_matches(state, rule):
                self._schedule_rule(rule_id, SENSOR_RULE_RETRY_SECONDS)
            return

        rule_state.update(
            {
                "task_created": True,
                "active_task_id": task.id,
                "last_task_created_at": triggered_at.isoformat(),
            }
        )
        await self._async_save()
        LOGGER.info(
            "Created Enaro task %s for Home Assistant sensor rule %s",
            task.id,
            rule_id,
        )

    def _initialize_rule_states(self, rules: list[dict[str, Any]]) -> None:
        rule_ids = {rule[CONF_RULE_ID] for rule in rules}
        self._rule_states = {
            rule_id: state
            for rule_id, state in self._rule_states.items()
            if rule_id in rule_ids
        }
        for rule in rules:
            rule_id = rule[CONF_RULE_ID]
            state = self.hass.states.get(rule[CONF_RULE_ENTITY_ID])
            matches = state is not None and _state_matches(state, rule)
            rule_state = self._rule_states.setdefault(rule_id, {})
            if matches:
                rule_state["incident_active"] = True
                rule_state.setdefault("task_created", False)
            else:
                rule_state.update(
                    {
                        "incident_active": False,
                        "task_created": False,
                        "active_task_id": None,
                    }
                )

    async def _async_save(self) -> None:
        await self._store.async_save({"rules": self._rule_states})


def _configured_rules(options: dict[str, Any]) -> list[dict[str, Any]]:
    rules: list[dict[str, Any]] = []
    for raw_rule in options.get(CONF_SENSOR_RULES, []):
        if not isinstance(raw_rule, dict) or not raw_rule.get(CONF_RULE_ENABLED, True):
            continue
        rule = dict(raw_rule)
        required_values = [
            rule.get(CONF_RULE_ID),
            rule.get(CONF_RULE_ENTITY_ID),
            rule.get(CONF_RULE_HOUSEHOLD_ID),
            rule.get(CONF_RULE_MEMBER_ID),
            rule.get(CONF_RULE_TARGET_STATE),
        ]
        if any(not value for value in required_values):
            continue
        rules.append(rule)
    return rules


def _rule_by_id(rules: list[dict[str, Any]], rule_id: str) -> dict[str, Any] | None:
    for rule in rules:
        if rule[CONF_RULE_ID] == rule_id:
            return rule
    return None


def _state_matches(state: State, rule: dict[str, Any]) -> bool:
    return state.state == str(rule[CONF_RULE_TARGET_STATE]).strip()


def _render_template(
    template: str,
    state: State,
    triggered_at: datetime,
    *,
    fallback: str,
) -> str:
    context = {
        "entity_id": state.entity_id,
        "entity_name": state.name or state.entity_id,
        "state": state.state,
        "triggered_at": triggered_at.astimezone().isoformat(timespec="seconds"),
    }
    try:
        return template.format(**context).strip()
    except (KeyError, ValueError):
        LOGGER.warning("Invalid Enaro sensor rule template: %s", template)
        return fallback


CALLBACK_TYPE = Any
