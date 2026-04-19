"""Shared entity base for Alby Hub."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import AlbyHubDataUpdateCoordinator


class AlbyHubCoordinatorEntity(CoordinatorEntity[AlbyHubDataUpdateCoordinator]):
    """Base entity bound to Alby Hub coordinator."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: AlbyHubDataUpdateCoordinator, entry_id: str) -> None:
        super().__init__(coordinator)
        self._entry_id = entry_id

    @property
    def device_info(self) -> DeviceInfo:
        """Return shared Alby Hub device info."""
        data = self.coordinator.data
        name = data.get("entry_name") or "Alby Hub"
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry_id)},
            name=name,
            manufacturer="Alby",
            model="Hub",
            sw_version=data.get("version"),
        )
