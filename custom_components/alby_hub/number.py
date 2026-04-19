"""Number platform for Alby Hub – invoice amount input."""

from __future__ import annotations

from homeassistant.components.number import NumberEntityDescription, NumberMode, RestoreNumber
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import NUMBER_KEY_INVOICE_AMOUNT
from .entity import AlbyHubCoordinatorEntity
from .helpers import get_runtime


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up invoice amount number entity."""
    runtime = get_runtime(hass, entry.entry_id)
    entities = [AlbyHubInvoiceAmountNumber(runtime.coordinator, entry.entry_id)]
    async_add_entities(entities)
    runtime.number_entities = {e.entity_description.key: e for e in entities}


class AlbyHubInvoiceAmountNumber(AlbyHubCoordinatorEntity, RestoreNumber):
    """Writable number entity for entering invoice amounts."""

    entity_description = NumberEntityDescription(
        key=NUMBER_KEY_INVOICE_AMOUNT,
        translation_key=NUMBER_KEY_INVOICE_AMOUNT,
        icon="mdi:currency-sign",
        native_min_value=0,
        native_max_value=100_000_000,
        native_step=1,
        mode=NumberMode.BOX,
    )

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_{NUMBER_KEY_INVOICE_AMOUNT}"
        self._attr_native_value: float = 0.0

    async def async_added_to_hass(self) -> None:
        """Restore previous value on startup."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_number_data()) is not None:
            self._attr_native_value = last.native_value or 0.0

    @property
    def native_value(self) -> float | None:
        """Return current number value."""
        return self._attr_native_value

    async def async_set_native_value(self, value: float) -> None:
        """Set number value (can be called by service handler or UI)."""
        self._attr_native_value = value
        self.async_write_ha_state()
