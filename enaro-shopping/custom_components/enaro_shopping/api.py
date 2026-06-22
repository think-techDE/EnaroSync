"""Async Enaro API client for Home Assistant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from aiohttp import ClientError, ClientSession
from homeassistant.exceptions import ConfigEntryAuthFailed, HomeAssistantError


class EnaroApiError(HomeAssistantError):
    """Raised when the Enaro API request fails."""


@dataclass(frozen=True)
class EnaroHousehold:
    """Enaro household visible to the configured account."""

    id: str
    name: str


@dataclass(frozen=True)
class EnaroHouseholdMember:
    """Enaro household member visible to the configured account."""

    id: str
    household_id: str
    display_name: str
    role: str
    is_virtual: bool


@dataclass(frozen=True)
class EnaroShoppingItem:
    """Enaro shopping list item."""

    id: str
    name: str
    status: str
    note: str | None
    amount: str | None
    unit: str | None
    category: str | None


@dataclass(frozen=True)
class EnaroShoppingList:
    """Enaro household shopping list."""

    id: str
    household: EnaroHousehold
    items: list[EnaroShoppingItem]


@dataclass(frozen=True)
class EnaroTask:
    """Enaro task."""

    id: str
    title: str
    status: str


class EnaroApiClient:
    """Small async API client for Enaro integration features."""

    def __init__(
        self,
        *,
        session: ClientSession,
        api_base_url: str,
        email: str,
        password: str,
    ) -> None:
        self._session = session
        self._api_base_url = api_base_url.rstrip("/")
        self._email = email
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None

    async def async_login(self) -> None:
        """Log in to Enaro."""
        payload = {
            "email": self._email,
            "password": self._password,
            "device_id": "home-assistant-enaro-integration",
            "platform": "home_assistant",
            "device_name": "Home Assistant Enaro Integration",
            "app_version": "ha-integration-0.2.5",
            "app_build_number": "7",
        }
        data = await self._request_raw("POST", "/api/v1/auth/login", json=payload)
        self._store_tokens(data)

    async def async_refresh(self) -> None:
        """Refresh the current access token."""
        if not self._refresh_token:
            raise ConfigEntryAuthFailed("No Enaro refresh token available")
        data = await self._request_raw(
            "POST",
            "/api/v1/auth/refresh",
            json={
                "refresh_token": self._refresh_token,
                "app_version": "ha-integration-0.2.5",
                "app_build_number": "7",
            },
        )
        self._store_tokens(data)

    async def async_validate_login(self) -> None:
        """Validate credentials for config flow."""
        await self.async_login()
        await self.async_list_households()

    async def async_list_households(self) -> list[EnaroHousehold]:
        """Return all Enaro households of the configured user."""
        data = await self._request("GET", "/api/v1/households")
        return [
            EnaroHousehold(id=str(item["id"]), name=str(item["name"])) for item in data
        ]

    async def async_get_shopping_list(
        self,
        household: EnaroHousehold,
    ) -> EnaroShoppingList:
        """Return the shopping list for one household."""
        data = await self._request(
            "GET",
            f"/api/v1/households/{household.id}/shopping-list",
        )
        items = [
            EnaroShoppingItem(
                id=str(item["id"]),
                name=str(item["name"]),
                status=str(item.get("status") or "open"),
                note=item.get("note"),
                amount=item.get("amount"),
                unit=item.get("unit"),
                category=item.get("category"),
            )
            for item in data.get("items", [])
        ]
        return EnaroShoppingList(
            id=str(data["id"]),
            household=household,
            items=items,
        )

    async def async_list_members(
        self,
        household_id: str,
    ) -> list[EnaroHouseholdMember]:
        """Return all members of one Enaro household."""
        data = await self._request("GET", f"/api/v1/households/{household_id}/members")
        return [
            EnaroHouseholdMember(
                id=str(item["id"]),
                household_id=str(item["household_id"]),
                display_name=str(item["display_name"]),
                role=str(item["role"]),
                is_virtual=bool(item.get("is_virtual") or False),
            )
            for item in data
        ]

    async def async_create_task(
        self,
        household_id: str,
        *,
        title: str,
        notes: str | None,
        assigned_member_ids: list[str],
        important: bool,
        due_at: datetime,
    ) -> EnaroTask:
        """Create an Enaro task."""
        data = await self._request(
            "POST",
            f"/api/v1/households/{household_id}/tasks",
            json={
                "title": title,
                "notes": notes,
                "assigned_member_ids": assigned_member_ids,
                "important": important,
                "due_at": due_at.isoformat(),
                "points": 0,
                "notify_assignees": True,
            },
        )
        return EnaroTask(
            id=str(data["id"]),
            title=str(data["title"]),
            status=str(data.get("status") or "open"),
        )

    async def async_create_item(
        self,
        household_id: str,
        *,
        name: str,
        note: str | None = None,
    ) -> EnaroShoppingItem:
        """Create a shopping item."""
        data = await self._request(
            "POST",
            f"/api/v1/households/{household_id}/shopping-list/items",
            json={"name": name, "note": note},
        )
        return _shopping_item_from_json(data)

    async def async_update_item(
        self,
        item_id: str,
        *,
        name: str | None = None,
        note: str | None = None,
        status: str | None = None,
    ) -> EnaroShoppingItem:
        """Update a shopping item."""
        payload = {
            key: value
            for key, value in {
                "name": name,
                "note": note,
                "status": status,
            }.items()
            if value is not None
        }
        data = await self._request(
            "PATCH",
            f"/api/v1/shopping-list-items/{item_id}",
            json=payload,
        )
        return _shopping_item_from_json(data)

    async def async_delete_items(self, item_ids: list[str]) -> None:
        """Delete shopping items."""
        for item_id in item_ids:
            await self._request("DELETE", f"/api/v1/shopping-list-items/{item_id}")

    async def _request(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
    ) -> Any:
        if self._access_token is None:
            await self.async_login()
        try:
            return await self._request_raw(method, path, json=json, authenticated=True)
        except ConfigEntryAuthFailed:
            await self.async_refresh()
            return await self._request_raw(method, path, json=json, authenticated=True)

    async def _request_raw(
        self,
        method: str,
        path: str,
        *,
        json: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> Any:
        headers = {}
        if authenticated and self._access_token:
            headers["Authorization"] = f"Bearer {self._access_token}"
        try:
            async with self._session.request(
                method,
                f"{self._api_base_url}{path}",
                json=json,
                headers=headers,
            ) as response:
                if response.status == 401:
                    raise ConfigEntryAuthFailed("Enaro credentials are invalid")
                if response.status >= 400:
                    detail = await _response_error_text(response)
                    raise EnaroApiError(
                        f"Enaro API {response.status} for {path}: {detail}"
                    )
                if response.status == 204:
                    return None
                return await response.json()
        except ClientError as err:
            raise EnaroApiError(f"Could not reach Enaro API: {err}") from err

    def _store_tokens(self, payload: dict[str, Any]) -> None:
        self._access_token = str(payload["access_token"])
        self._refresh_token = str(payload["refresh_token"])


async def _response_error_text(response: Any) -> str:
    try:
        payload = await response.json()
        detail = payload.get("detail")
        if isinstance(detail, dict):
            return str(detail.get("message") or detail.get("code") or payload)
        return str(detail or payload)
    except (ValueError, TypeError):
        return await response.text()


def _shopping_item_from_json(data: dict[str, Any]) -> EnaroShoppingItem:
    return EnaroShoppingItem(
        id=str(data["id"]),
        name=str(data["name"]),
        status=str(data.get("status") or "open"),
        note=data.get("note"),
        amount=data.get("amount"),
        unit=data.get("unit"),
        category=data.get("category"),
    )
