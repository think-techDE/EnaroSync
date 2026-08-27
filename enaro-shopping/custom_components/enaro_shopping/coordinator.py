"""Coordinator for Enaro shopping lists and wallboard summaries."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import EnaroApiClient, EnaroApiError, EnaroShoppingList
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

LOGGER = logging.getLogger(__name__)


class EnaroShoppingCoordinator(DataUpdateCoordinator[dict[str, EnaroShoppingList]]):
    """Fetch Enaro households and shopping lists."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: EnaroApiClient,
        entry_id: str,
    ) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client
        self.entry_id = entry_id
        self.wallboards: dict[str, dict[str, Any]] = {}
        self.wallboard_online: dict[str, bool] = {}
        self.last_successful_at: str | None = None
        self._store: Store[dict[str, Any]] = Store(
            hass,
            1,
            f"{DOMAIN}.{entry_id}.wallboard",
        )

    async def async_load_wallboard_cache(self) -> None:
        """Load the last successful summaries before the first API refresh."""
        stored = await self._store.async_load()
        if not isinstance(stored, dict):
            return
        wallboards = stored.get("wallboards")
        if isinstance(wallboards, dict):
            self.wallboards = {
                str(key): dict(value)
                for key, value in wallboards.items()
                if isinstance(value, dict)
            }
            self.wallboard_online = {key: False for key in self.wallboards}
        last_successful_at = stored.get("last_successful_at")
        if isinstance(last_successful_at, str):
            self.last_successful_at = last_successful_at

    async def _async_update_data(self) -> dict[str, EnaroShoppingList]:
        try:
            households = await self.client.async_list_households()
        except EnaroApiError:
            LOGGER.warning("Enaro API unavailable; retaining cached wallboard data")
            self.wallboard_online = {key: False for key in self.wallboards}
            if self.data is not None or self.wallboards:
                return self.data or {}
            raise
        lists: dict[str, EnaroShoppingList] = {}
        for household in households:
            try:
                lists[household.id] = await self.client.async_get_shopping_list(
                    household
                )
            except EnaroApiError as err:
                LOGGER.warning(
                    "Shopping list for household %s unavailable: %s",
                    household.id,
                    err,
                )
                if self.data is not None and household.id in self.data:
                    lists[household.id] = self.data[household.id]
                self.wallboard_online[household.id] = False
            try:
                self.wallboards[household.id] = await self.client.async_get_wallboard(
                    household.id
                )
                self.wallboard_online[household.id] = True
            except EnaroApiError as err:
                LOGGER.warning(
                    "Wallboard for household %s unavailable: %s",
                    household.id,
                    err,
                )
                self.wallboard_online[household.id] = False
        current_ids = {household.id for household in households}
        self.wallboards = {
            key: value for key, value in self.wallboards.items() if key in current_ids
        }
        self.wallboard_online = {
            key: value for key, value in self.wallboard_online.items() if key in current_ids
        }
        if any(self.wallboard_online.values()):
            self.last_successful_at = datetime.now(UTC).isoformat()
            await self._store.async_save(
                {
                    "wallboards": self.wallboards,
                    "last_successful_at": self.last_successful_at,
                }
            )
        return lists
