"""Coordinator for Enaro shopping lists."""

from __future__ import annotations

import logging

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .api import EnaroApiClient, EnaroShoppingList
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

LOGGER = logging.getLogger(__name__)


class EnaroShoppingCoordinator(DataUpdateCoordinator[dict[str, EnaroShoppingList]]):
    """Fetch Enaro households and shopping lists."""

    def __init__(self, hass: HomeAssistant, client: EnaroApiClient) -> None:
        super().__init__(
            hass,
            LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, EnaroShoppingList]:
        households = await self.client.async_list_households()
        lists: dict[str, EnaroShoppingList] = {}
        for household in households:
            shopping_list = await self.client.async_get_shopping_list(household)
            lists[household.id] = shopping_list
        return lists
