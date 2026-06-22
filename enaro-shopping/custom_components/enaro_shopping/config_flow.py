"""Config flow for Enaro Integration."""

from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
import logging
from typing import Any
from uuid import uuid4

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .api import EnaroApiClient, EnaroApiError, EnaroHousehold, EnaroHouseholdMember
from .const import (
    CONF_API_BASE_URL,
    CONF_EMAIL,
    CONF_PASSWORD,
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
    DEFAULT_API_BASE_URL,
    DEFAULT_SENSOR_RULE_NOTES_TEMPLATE,
    DEFAULT_SENSOR_RULE_TARGET_STATE,
    DEFAULT_SENSOR_RULE_TITLE_TEMPLATE,
    DOMAIN,
    SENSOR_STATE_HISTORY_DAYS,
)

LOGGER = logging.getLogger(__name__)


class EnaroShoppingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Enaro Integration config flow."""

    VERSION = 1

    async def async_step_user(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            client = EnaroApiClient(
                session=async_get_clientsession(self.hass),
                api_base_url=user_input[CONF_API_BASE_URL],
                email=user_input[CONF_EMAIL],
                password=user_input[CONF_PASSWORD],
            )
            try:
                await client.async_validate_login()
            except ConfigEntryAuthFailed:
                errors["base"] = "invalid_auth"
            except EnaroApiError:
                errors["base"] = "cannot_connect"
            except Exception:  # noqa: BLE001
                errors["base"] = "unknown"
            else:
                await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=f"Enaro Integration ({user_input[CONF_EMAIL]})",
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_API_BASE_URL, default=DEFAULT_API_BASE_URL): str,
                    vol.Required(CONF_EMAIL): str,
                    vol.Required(CONF_PASSWORD): str,
                }
            ),
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Create the options flow."""
        return EnaroShoppingOptionsFlow(config_entry)


class EnaroShoppingOptionsFlow(config_entries.OptionsFlow):
    """Manage Enaro Integration options."""

    def __init__(self, config_entry: ConfigEntry) -> None:
        self._config_entry = config_entry
        self._selected_household_id: str | None = None
        self._selected_entity_id: str | None = None

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Show the options menu."""
        rules = _rules_from_options(self._config_entry.options)
        menu_options = ["add_rule"]
        if rules:
            menu_options.append("toggle_rule")
            menu_options.append("remove_rule")
        return self.async_show_menu(
            step_id="init",
            menu_options=menu_options,
            description_placeholders={"rule_count": str(len(rules))},
        )

    async def async_step_add_rule(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Choose the Enaro household for a new sensor rule."""
        errors: dict[str, str] = {}
        try:
            households = await self._async_households()
        except (ConfigEntryAuthFailed, EnaroApiError):
            households = []
            errors["base"] = "cannot_connect"

        if user_input is not None and not errors:
            self._selected_household_id = user_input[CONF_RULE_HOUSEHOLD_ID]
            return await self.async_step_add_rule_sensor()

        return self.async_show_form(
            step_id="add_rule",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RULE_HOUSEHOLD_ID): _select_schema(
                        [
                            selector.SelectOptionDict(
                                value=household.id,
                                label=household.name,
                            )
                            for household in households
                        ]
                    )
                }
            ),
            errors=errors,
        )

    async def async_step_add_rule_sensor(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Choose the Home Assistant entity for a new sensor rule."""
        if self._selected_household_id is None:
            return await self.async_step_add_rule()

        if user_input is not None:
            self._selected_entity_id = user_input[CONF_RULE_ENTITY_ID]
            return await self.async_step_add_rule_details()

        return self.async_show_form(
            step_id="add_rule_sensor",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RULE_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig()
                    )
                }
            ),
        )

    async def async_step_add_rule_details(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Configure a new sensor rule."""
        if self._selected_household_id is None:
            return await self.async_step_add_rule()
        if self._selected_entity_id is None:
            return await self.async_step_add_rule_sensor()

        errors: dict[str, str] = {}
        try:
            members = await self._async_members(self._selected_household_id)
        except (ConfigEntryAuthFailed, EnaroApiError):
            members = []
            errors["base"] = "cannot_connect"
        observed_states = await self._async_observed_states(self._selected_entity_id)

        if user_input is not None and not errors:
            rule = {
                CONF_RULE_ID: uuid4().hex,
                CONF_RULE_ENABLED: user_input[CONF_RULE_ENABLED],
                CONF_RULE_ENTITY_ID: self._selected_entity_id,
                CONF_RULE_HOUSEHOLD_ID: self._selected_household_id,
                CONF_RULE_MEMBER_ID: user_input[CONF_RULE_MEMBER_ID],
                CONF_RULE_TARGET_STATE: user_input[
                    CONF_RULE_TARGET_STATE
                ].strip()
                or DEFAULT_SENSOR_RULE_TARGET_STATE,
                CONF_RULE_IMPORTANT: user_input[CONF_RULE_IMPORTANT],
                CONF_RULE_TITLE_TEMPLATE: user_input[
                    CONF_RULE_TITLE_TEMPLATE
                ].strip()
                or DEFAULT_SENSOR_RULE_TITLE_TEMPLATE,
                CONF_RULE_NOTES_TEMPLATE: user_input[
                    CONF_RULE_NOTES_TEMPLATE
                ].strip(),
            }
            options = dict(self._config_entry.options)
            rules = _rules_from_options(options)
            rules.append(rule)
            options[CONF_SENSOR_RULES] = rules
            return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="add_rule_details",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RULE_ENABLED, default=True): bool,
                    vol.Required(CONF_RULE_TARGET_STATE): _target_state_schema(
                        observed_states
                    ),
                    vol.Required(CONF_RULE_MEMBER_ID): _select_schema(
                        [
                            selector.SelectOptionDict(
                                value=member.id,
                                label=f"{member.display_name} ({member.role})",
                            )
                            for member in members
                        ]
                    ),
                    vol.Required(CONF_RULE_IMPORTANT, default=False): bool,
                    vol.Required(
                        CONF_RULE_TITLE_TEMPLATE,
                        default=DEFAULT_SENSOR_RULE_TITLE_TEMPLATE,
                    ): str,
                    vol.Required(
                        CONF_RULE_NOTES_TEMPLATE,
                        default=DEFAULT_SENSOR_RULE_NOTES_TEMPLATE,
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_remove_rule(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Remove a configured sensor rule."""
        rules = _rules_from_options(self._config_entry.options)
        if user_input is not None:
            rule_id = user_input[CONF_RULE_ID]
            options = dict(self._config_entry.options)
            options[CONF_SENSOR_RULES] = [
                rule for rule in rules if rule.get(CONF_RULE_ID) != rule_id
            ]
            return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="remove_rule",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RULE_ID): _select_schema(
                        [
                            selector.SelectOptionDict(
                                value=str(rule[CONF_RULE_ID]),
                                label=_rule_label(rule),
                            )
                            for rule in rules
                        ]
                    )
                }
            ),
        )

    async def async_step_toggle_rule(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Enable or disable a configured sensor rule."""
        rules = _rules_from_options(self._config_entry.options)
        if user_input is not None:
            rule_id = user_input[CONF_RULE_ID]
            options = dict(self._config_entry.options)
            updated_rules = []
            for rule in rules:
                if rule.get(CONF_RULE_ID) == rule_id:
                    updated_rule = dict(rule)
                    updated_rule[CONF_RULE_ENABLED] = bool(
                        user_input[CONF_RULE_ENABLED]
                    )
                    updated_rules.append(updated_rule)
                else:
                    updated_rules.append(rule)
            options[CONF_SENSOR_RULES] = updated_rules
            return self.async_create_entry(title="", data=options)

        return self.async_show_form(
            step_id="toggle_rule",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_RULE_ID): _select_schema(
                        [
                            selector.SelectOptionDict(
                                value=str(rule[CONF_RULE_ID]),
                                label=_rule_label(rule),
                            )
                            for rule in rules
                        ]
                    ),
                    vol.Required(CONF_RULE_ENABLED, default=True): bool,
                }
            ),
        )

    def _async_client(self) -> EnaroApiClient:
        return EnaroApiClient(
            session=async_get_clientsession(self.hass),
            api_base_url=self._config_entry.data[CONF_API_BASE_URL],
            email=self._config_entry.data[CONF_EMAIL],
            password=self._config_entry.data[CONF_PASSWORD],
        )

    async def _async_households(self) -> list[EnaroHousehold]:
        return await self._async_client().async_list_households()

    async def _async_members(self, household_id: str) -> list[EnaroHouseholdMember]:
        return await self._async_client().async_list_members(household_id)

    async def _async_observed_states(self, entity_id: str) -> list[str]:
        states = set[str]()
        if (current_state := self.hass.states.get(entity_id)) is not None:
            states.add(current_state.state)
        states.update(await _async_history_states(self.hass, entity_id))
        return sorted(states, key=_state_sort_key)


def _select_schema(options: list[selector.SelectOptionDict]) -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=options,
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _target_state_schema(states: list[str]) -> vol.Any:
    if not states:
        return str
    options = [
        selector.SelectOptionDict(value=state, label=state)
        for state in states
        if state
    ]
    if not options:
        return str
    return _select_schema(options)


def _rules_from_options(options: Mapping[str, Any]) -> list[dict[str, Any]]:
    raw_rules = options.get(CONF_SENSOR_RULES, [])
    return [dict(rule) for rule in raw_rules if isinstance(rule, dict)]


def _rule_label(rule: dict[str, Any]) -> str:
    entity_id = str(rule.get(CONF_RULE_ENTITY_ID) or "Sensor")
    target_state = str(rule.get(CONF_RULE_TARGET_STATE) or "")
    title = str(rule.get(CONF_RULE_TITLE_TEMPLATE) or entity_id)
    enabled = bool(rule.get(CONF_RULE_ENABLED, True))
    prefix = "Aktiv" if enabled else "Inaktiv"
    return f"{prefix}: {entity_id} = {target_state} -> {title}"


async def _async_history_states(hass, entity_id: str) -> list[str]:
    try:
        from homeassistant.components.recorder import get_instance, history
        from homeassistant.components.recorder.util import session_scope
    except ImportError:
        return []

    end_time = dt_util.utcnow()
    start_time = end_time - timedelta(days=SENSOR_STATE_HISTORY_DAYS)

    def _load_states() -> list[str]:
        with session_scope(hass=hass, read_only=True) as session:
            rows_by_entity = history.get_significant_states_with_session(
                hass,
                session,
                start_time,
                end_time,
                [entity_id],
                None,
                True,
                True,
                True,
                True,
            )
        return [_state_value(row) for row in rows_by_entity.get(entity_id, [])]

    try:
        return [
            state
            for state in await get_instance(hass).async_add_executor_job(_load_states)
            if state
        ]
    except Exception as err:  # noqa: BLE001
        LOGGER.debug("Could not load history states for %s: %s", entity_id, err)
        return []


def _state_value(row: Any) -> str:
    if isinstance(row, dict):
        return str(row.get("state") or "")
    return str(getattr(row, "state", "") or "")


def _state_sort_key(state: str) -> tuple[int, str]:
    common_order = {
        "unavailable": 0,
        "unknown": 1,
        "on": 2,
        "off": 3,
    }
    return (common_order.get(state, 100), state)
