"""To-do platform for Enaro shopping lists."""

from __future__ import annotations

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .api import EnaroShoppingItem, EnaroShoppingList
from .const import DOMAIN
from .coordinator import EnaroShoppingCoordinator


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enaro shopping To-do entities."""
    coordinator: EnaroShoppingCoordinator = hass.data[DOMAIN][entry.entry_id]
    known_household_ids: set[str] = set()

    @callback
    def add_missing_entities() -> None:
        new_entities = []
        if coordinator.data is None:
            return
        for household_id, shopping_list in coordinator.data.items():
            if household_id in known_household_ids:
                continue
            known_household_ids.add(household_id)
            new_entities.append(EnaroShoppingTodoEntity(coordinator, shopping_list))
        if new_entities:
            async_add_entities(new_entities)

    add_missing_entities()
    entry.async_on_unload(coordinator.async_add_listener(add_missing_entities))


class EnaroShoppingTodoEntity(
    CoordinatorEntity[EnaroShoppingCoordinator],
    TodoListEntity,
):
    """One Home Assistant To-do list per Enaro household."""

    _attr_has_entity_name = True
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(
        self,
        coordinator: EnaroShoppingCoordinator,
        shopping_list: EnaroShoppingList,
    ) -> None:
        super().__init__(coordinator)
        self._household_id = shopping_list.household.id
        self._attr_name = f"{shopping_list.household.name} Einkauf"
        self._attr_unique_id = f"enaro_shopping_{shopping_list.household.id}"
        self.entity_id = f"todo.enaro_{slugify(shopping_list.household.name)}_einkauf"
        self._apply_items(shopping_list)

    @property
    def available(self) -> bool:
        """Return if the entity is available."""
        return (
            self.coordinator.data is not None
            and self._household_id in self.coordinator.data
        )

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Create an Enaro shopping item."""
        if not item.summary:
            return
        created = await self.coordinator.client.async_create_item(
            self._household_id,
            name=item.summary,
            note=item.description,
        )
        if item.status == TodoItemStatus.COMPLETED:
            await self.coordinator.client.async_update_item(
                created.id,
                status="checked",
            )
        await self.coordinator.async_request_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Update an Enaro shopping item."""
        if not item.uid:
            return
        await self.coordinator.client.async_update_item(
            item.uid,
            name=item.summary,
            note=item.description,
            status=_enaro_status_from_todo(item.status),
        )
        await self.coordinator.async_request_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Delete Enaro shopping items."""
        await self.coordinator.client.async_delete_items(uids)
        await self.coordinator.async_request_refresh()

    @callback
    def _handle_coordinator_update(self) -> None:
        if self.coordinator.data is not None and (
            shopping_list := self.coordinator.data.get(self._household_id)
        ):
            self._attr_name = f"{shopping_list.household.name} Einkauf"
            self._apply_items(shopping_list)
        super()._handle_coordinator_update()

    def _apply_items(self, shopping_list: EnaroShoppingList) -> None:
        self._attr_todo_items = [
            _todo_item_from_enaro(item) for item in shopping_list.items
        ]


def _todo_item_from_enaro(item: EnaroShoppingItem) -> TodoItem:
    return TodoItem(
        uid=item.id,
        summary=item.name,
        status=_todo_status_from_enaro(item.status),
        description=item.note,
    )


def _todo_status_from_enaro(status: str) -> TodoItemStatus:
    if status == "checked":
        return TodoItemStatus.COMPLETED
    return TodoItemStatus.NEEDS_ACTION


def _enaro_status_from_todo(status: TodoItemStatus | None) -> str | None:
    if status == TodoItemStatus.COMPLETED:
        return "checked"
    if status == TodoItemStatus.NEEDS_ACTION:
        return "open"
    return None
