"""Text platform for Alby Hub – invoice input and last-invoice display."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from homeassistant.components.text import RestoreText, TextEntity, TextEntityDescription, TextMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN, TEXT_KEY_INVOICE_INPUT, TEXT_KEY_LAST_INVOICE
from .entity import AlbyHubCoordinatorEntity
from .helpers import get_runtime


@dataclass(frozen=True, kw_only=True)
class AlbyHubTextDescription(TextEntityDescription):
    """Extended description for Alby Hub text entities."""

    read_only: bool = False


TEXT_DESCRIPTIONS: tuple[AlbyHubTextDescription, ...] = (
    AlbyHubTextDescription(
        key=TEXT_KEY_INVOICE_INPUT,
        translation_key=TEXT_KEY_INVOICE_INPUT,
        icon="mdi:clipboard-text-outline",
        native_min=0,
        native_max=2048,
        mode=TextMode.TEXT,
        read_only=False,
    ),
    AlbyHubTextDescription(
        key=TEXT_KEY_LAST_INVOICE,
        translation_key=TEXT_KEY_LAST_INVOICE,
        icon="mdi:qrcode",
        native_min=0,
        native_max=2048,
        mode=TextMode.TEXT,
        read_only=False,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Alby Hub text entities from a config entry."""
    runtime = get_runtime(hass, entry.entry_id)
    entities = [
        AlbyHubTextEntity(runtime.coordinator, entry.entry_id, desc)
        for desc in TEXT_DESCRIPTIONS
    ]
    async_add_entities(entities)
    # Store references so services can update them
    runtime.text_entities = {e.entity_description.key: e for e in entities}


class AlbyHubTextEntity(AlbyHubCoordinatorEntity, RestoreText):
    """Writable text entity for Alby Hub invoice workflow."""

    entity_description: AlbyHubTextDescription

    def __init__(self, coordinator, entry_id: str, description: AlbyHubTextDescription) -> None:
        super().__init__(coordinator, entry_id)
        self.entity_description = description
        self._attr_unique_id = f"{entry_id}_{description.key}"
        self._attr_native_value = ""

    async def async_added_to_hass(self) -> None:
        """Restore previous value on startup."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_text_data()) is not None:
            self._attr_native_value = last.native_value or ""

    @property
    def native_value(self) -> str:
        """Return current text value."""
        return self._attr_native_value

    async def async_set_value(self, value: str) -> None:
        """Set text value (can be called by service handler or UI)."""
        self._attr_native_value = value
        self.async_write_ha_state()
