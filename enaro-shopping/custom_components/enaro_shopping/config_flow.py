"""Config flow for Enaro Shopping."""

from __future__ import annotations

from typing import Any

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import EnaroApiClient, EnaroApiError
from .const import (
    CONF_API_BASE_URL,
    CONF_EMAIL,
    CONF_PASSWORD,
    DEFAULT_API_BASE_URL,
    DOMAIN,
)


class EnaroShoppingConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Enaro Shopping config flow."""

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
                    title=f"Enaro Einkauf ({user_input[CONF_EMAIL]})",
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
    """Options flow placeholder for Enaro Shopping."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(
        self,
        user_input: dict[str, Any] | None = None,
    ) -> config_entries.ConfigFlowResult:
        """Manage options."""
        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({}),
        )
