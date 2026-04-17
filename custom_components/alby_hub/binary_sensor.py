"""Binary sensor platform for Alby Hub."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import AlbyHubCoordinatorEntity
from .helpers import get_runtime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alby Hub binary sensors."""
    runtime = get_runtime(hass, entry.entry_id)
    async_add_entities([AlbyHubConnectionBinarySensor(runtime.coordinator, entry.entry_id)])


class AlbyHubConnectionBinarySensor(AlbyHubCoordinatorEntity, BinarySensorEntity):
    """Represents connection state to Alby Hub."""

    _attr_translation_key = "node_online"
    _attr_icon = "mdi:lan-connect"

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_node_online"

    @property
    def is_on(self) -> bool:
        """Return True if hub is reachable."""
        return bool(self.coordinator.data.get("connected"))
