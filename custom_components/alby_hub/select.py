"""Select platform for Alby Hub – invoice amount unit selection."""

from __future__ import annotations

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import SELECT_KEY_INVOICE_AMOUNT_UNIT
from .entity import AlbyHubCoordinatorEntity
from .helpers import get_runtime

_DEFAULT_UNIT = "SAT"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up invoice amount unit select entity."""
    runtime = get_runtime(hass, entry.entry_id)
    entities = [AlbyHubInvoiceAmountUnitSelect(runtime.coordinator, entry.entry_id)]
    async_add_entities(entities)
    runtime.select_entities = {e.entity_description.key: e for e in entities}


class AlbyHubInvoiceAmountUnitSelect(AlbyHubCoordinatorEntity, RestoreEntity, SelectEntity):
    """Select entity for choosing the unit of the invoice amount (SAT / BTC / Fiat)."""

    entity_description = SelectEntityDescription(
        key=SELECT_KEY_INVOICE_AMOUNT_UNIT,
        translation_key=SELECT_KEY_INVOICE_AMOUNT_UNIT,
        icon="mdi:scale-balance",
    )

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_{SELECT_KEY_INVOICE_AMOUNT_UNIT}"
        self._attr_current_option: str = _DEFAULT_UNIT

    @property
    def options(self) -> list[str]:
        """Return selectable units: SAT, BTC, and the configured fiat currency."""
        base: list[str] = ["SAT", "BTC"]
        fiat = self.coordinator.data.get("price_currency")
        if fiat and fiat not in base:
            base.append(fiat)
        return base

    @property
    def current_option(self) -> str | None:
        """Return the currently selected unit."""
        # If stored option is no longer valid (e.g. currency changed), fall back to SAT
        if self._attr_current_option not in self.options:
            return "SAT"
        return self._attr_current_option

    async def async_added_to_hass(self) -> None:
        """Restore previously selected unit."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state:
            self._attr_current_option = last.state

    async def async_select_option(self, option: str) -> None:
        """Handle user selecting a unit."""
        self._attr_current_option = option
        self.async_write_ha_state()
