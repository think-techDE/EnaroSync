"""To-do platform for Enaro shopping lists."""

from __future__ import annotations

from uuid import uuid4

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant, callback
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt as dt_util
from homeassistant.util import slugify

from .api import EnaroShoppingItem, EnaroShoppingList
from .const import DATA_COORDINATOR, DOMAIN
from .coordinator import EnaroShoppingCoordinator
from .item_names import format_shopping_item_name


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Enaro shopping To-do entities."""
    coordinator: EnaroShoppingCoordinator = hass.data[DOMAIN][entry.entry_id][
        DATA_COORDINATOR
    ]
    known_shopping_household_ids: set[str] = set()
    known_wallboard_members: set[tuple[str, str]] = set()

    @callback
    def add_missing_entities() -> None:
        new_entities = []
        if coordinator.data is not None:
            for household_id, shopping_list in coordinator.data.items():
                if household_id in known_shopping_household_ids:
                    continue
                known_shopping_household_ids.add(household_id)
                new_entities.append(EnaroShoppingTodoEntity(coordinator, shopping_list))
        for household_id, wallboard in coordinator.wallboards.items():
            for member in wallboard.get("members", []):
                member_id = str(member.get("member_id") or "")
                key = (household_id, member_id)
                if not member_id or key in known_wallboard_members:
                    continue
                known_wallboard_members.add(key)
                new_entities.append(
                    EnaroWallboardTaskTodoEntity(
                        coordinator,
                        household_id=household_id,
                        household_name=str(wallboard.get("household_name") or "Enaro"),
                        member=member,
                    )
                )
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
        name = format_shopping_item_name(item.summary)
        if not name:
            return
        created = await self.coordinator.client.async_create_item(
            self._household_id,
            name=name,
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
        name = (
            format_shopping_item_name(item.summary)
            if item.summary is not None
            else None
        )
        await self.coordinator.client.async_update_item(
            item.uid,
            name=name,
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


class EnaroWallboardTaskTodoEntity(
    CoordinatorEntity[EnaroShoppingCoordinator],
    TodoListEntity,
):
    """Wallboard tasks for one explicitly shared Enaro member."""

    _attr_has_entity_name = True
    _attr_supported_features = TodoListEntityFeature.UPDATE_TODO_ITEM

    def __init__(
        self,
        coordinator: EnaroShoppingCoordinator,
        *,
        household_id: str,
        household_name: str,
        member: dict,
    ) -> None:
        super().__init__(coordinator)
        self._household_id = household_id
        self._household_name = household_name
        self._member_id = str(member["member_id"])
        self._member_name = str(member["display_name"])
        self._is_virtual = bool(member.get("is_virtual") or False)
        self._attr_name = f"{household_name} Aufgaben {self._member_name}"
        self._attr_unique_id = (
            f"enaro_wallboard_tasks_{household_id}_{self._member_id}"
        )
        self.entity_id = (
            f"todo.enaro_{slugify(household_name)}_aufgaben_"
            f"{slugify(self._member_name)}"
        )
        self._apply_wallboard()

    @property
    def available(self) -> bool:
        """Disable actions while the API is unavailable or sharing ended."""
        return bool(
            self.coordinator.wallboard_online.get(self._household_id, False)
            and self._current_member is not None
        )

    @property
    def extra_state_attributes(self) -> dict:
        """Expose stable identifiers for the bundled wallboard card."""
        return {
            "enaro_household_id": self._household_id,
            "enaro_member_id": self._member_id,
            "enaro_member_name": self._member_name,
            "enaro_is_virtual": self._is_virtual,
        }

    @property
    def device_info(self) -> dict:
        """Attach all Enaro entities to the integration device."""
        return {
            "identifiers": {(DOMAIN, self.coordinator.entry_id)},
            "name": "Enaro Integration",
            "manufacturer": "Think-Tech",
            "model": "Enaro Home Assistant Integration",
            "sw_version": "0.3.1",
            "configuration_url": "https://github.com/think-techDE/EnaroSync",
        }

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Only completion is supported from the shared display."""
        if not item.uid or item.status != TodoItemStatus.COMPLETED:
            raise HomeAssistantError(
                "Enaro wallboard tasks can only be completed, not edited or reopened."
            )
        if not self.available:
            raise HomeAssistantError("Enaro is offline; wallboard actions are disabled.")
        response = await self.coordinator.client.async_complete_wallboard_task(
            self._household_id,
            item.uid,
            completed_by_member_id=self._member_id,
            client_request_id=f"ha-wallboard-{uuid4()}",
        )
        self._apply_action_response(response)

    async def async_snooze_task(self, uid: str, preset: str) -> None:
        """Snooze a wallboard task via the entity service."""
        if not self.available:
            raise HomeAssistantError("Enaro is offline; wallboard actions are disabled.")
        if not self._contains_task(uid):
            raise HomeAssistantError("Task is not assigned to this wallboard member.")
        response = await self.coordinator.client.async_snooze_wallboard_task(
            self._household_id,
            uid,
            preset=preset,
        )
        self._apply_action_response(response)

    @callback
    def _handle_coordinator_update(self) -> None:
        self._apply_wallboard()
        super()._handle_coordinator_update()

    @property
    def _current_member(self) -> dict | None:
        wallboard = self.coordinator.wallboards.get(self._household_id, {})
        return next(
            (
                item
                for item in wallboard.get("members", [])
                if str(item.get("member_id")) == self._member_id
            ),
            None,
        )

    def _contains_task(self, task_id: str) -> bool:
        wallboard = self.coordinator.wallboards.get(self._household_id, {})
        return any(
            str(task.get("id")) == task_id
            and self._member_id in task.get("completion_member_ids", [])
            for task in wallboard.get("tasks", [])
        )

    def _apply_action_response(self, response: dict) -> None:
        wallboard = response.get("wallboard")
        if isinstance(wallboard, dict):
            self.coordinator.wallboards[self._household_id] = wallboard
            self.coordinator.wallboard_online[self._household_id] = True
            self.coordinator.async_set_updated_data(self.coordinator.data or {})

    def _apply_wallboard(self) -> None:
        wallboard = self.coordinator.wallboards.get(self._household_id, {})
        if (member := self._current_member) is not None:
            self._member_name = str(member.get("display_name") or self._member_name)
            self._is_virtual = bool(member.get("is_virtual") or False)
            self._attr_name = f"{self._household_name} Aufgaben {self._member_name}"
            tasks = [
                task
                for task in wallboard.get("tasks", [])
                if self._member_id in task.get("member_ids", [])
            ]
        else:
            tasks = []
        self._attr_todo_items = [_todo_item_from_wallboard(task) for task in tasks]


def _todo_item_from_wallboard(task: dict) -> TodoItem:
    due = None
    if isinstance(task.get("due_at"), str):
        due = dt_util.parse_datetime(task["due_at"])
    notes = str(task.get("notes") or "").strip() or None
    if task.get("assignment_mode") == "rotating":
        current = task.get("rotation_current_member_name")
        next_name = task.get("rotation_next_member_name")
        rotation_note = f"Aktuell: {current or '-'}"
        if next_name:
            rotation_note += f" · Als Naechstes: {next_name}"
        notes = f"{notes}\n{rotation_note}" if notes else rotation_note
    return TodoItem(
        uid=str(task["id"]),
        summary=str(task["title"]),
        status=TodoItemStatus.NEEDS_ACTION,
        description=notes,
        due=due,
    )


def _todo_item_from_enaro(item: EnaroShoppingItem) -> TodoItem:
    return TodoItem(
        uid=item.id,
        summary=format_shopping_item_name(item.name),
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
