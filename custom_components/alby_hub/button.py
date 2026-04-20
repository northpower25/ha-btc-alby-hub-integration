"""Button platform for Alby Hub – create invoice trigger."""

from __future__ import annotations

import logging
from decimal import Decimal, InvalidOperation

from homeassistant.components.button import ButtonEntity, ButtonEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .api import AlbyHubApiError
from .const import (
    BUTTON_KEY_CREATE_INVOICE,
    MODE_EXPERT,
    NUMBER_KEY_INVOICE_AMOUNT,
    SATS_PER_BTC,
    SELECT_KEY_INVOICE_AMOUNT_UNIT,
)
from .entity import AlbyHubCoordinatorEntity
from .helpers import get_runtime
from .nwc_client import async_nwc_request

_LOGGER = logging.getLogger(__name__)
_MSATS_PER_SAT = 1000


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up the create-invoice button entity."""
    runtime = get_runtime(hass, entry.entry_id)
    async_add_entities([AlbyHubCreateInvoiceButton(runtime.coordinator, entry.entry_id)])


class AlbyHubCreateInvoiceButton(AlbyHubCoordinatorEntity, ButtonEntity):
    """Button that creates a Lightning invoice using the current amount/unit entities."""

    entity_description = ButtonEntityDescription(
        key=BUTTON_KEY_CREATE_INVOICE,
        translation_key=BUTTON_KEY_CREATE_INVOICE,
        icon="mdi:receipt-text-plus",
    )

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_{BUTTON_KEY_CREATE_INVOICE}"

    async def async_press(self) -> None:
        """Create a Lightning invoice for the configured amount."""
        runtime = get_runtime(self.hass, self._entry_id)

        # Read amount and unit from sibling entities
        amount_entity = runtime.number_entities.get(NUMBER_KEY_INVOICE_AMOUNT)
        unit_entity = runtime.select_entities.get(SELECT_KEY_INVOICE_AMOUNT_UNIT)
        amount_val = float(amount_entity.native_value or 0) if amount_entity else 0.0
        unit = unit_entity.current_option or "SAT" if unit_entity else "SAT"

        amount_sat = _resolve_sats(amount_val, unit, self.coordinator.data)
        _LOGGER.debug(
            "Creating invoice: %.8g %s → %d sat", amount_val, unit, amount_sat
        )

        mode = self.coordinator.data.get("mode")
        invoice_str = ""

        if mode == MODE_EXPERT and runtime.api_client is not None:
            try:
                result = await runtime.api_client.create_invoice(
                    amount_sat=amount_sat, memo=None, expiry_seconds=None
                )
            except AlbyHubApiError as err:
                raise HomeAssistantError(f"Failed to create invoice: {err}") from err
            invoice_str = result.get("payment_request") or result.get("invoice") or ""
        else:
            # Cloud / NWC mode
            result = await async_nwc_request(
                runtime.session,
                runtime.nwc_info,
                "make_invoice",
                {"amount": amount_sat * _MSATS_PER_SAT},
            )
            if result is None or result.get("error"):
                raise HomeAssistantError(
                    f"NWC make_invoice failed: {result.get('error') if result else 'no response'}"
                )
            inv_result = result.get("result") or {}
            invoice_str = inv_result.get("invoice") or inv_result.get("payment_request") or ""

        if not invoice_str:
            raise HomeAssistantError("Invoice created but no payment_request returned")

        if runtime.last_invoice_entity is not None:
            await runtime.last_invoice_entity.async_set_invoice(invoice_str)

        _LOGGER.debug("Invoice stored: %s…", invoice_str[:20])


def _resolve_sats(amount: float, unit: str, coordinator_data: dict) -> int:
    """Convert amount in the given unit to satoshis. Raises HomeAssistantError on failure."""
    try:
        if unit == "SAT":
            sats = max(1, int(amount))
        elif unit == "BTC":
            sats = max(1, int(Decimal(str(amount)) * Decimal(SATS_PER_BTC)))
        else:
            # Treat as fiat
            btc_price = coordinator_data.get("bitcoin_price")
            if not btc_price or float(btc_price) <= 0:
                raise HomeAssistantError(
                    "Cannot convert fiat amount: Bitcoin price sensor is unavailable. "
                    "Check your price provider configuration."
                )
            sats = max(
                1,
                int(
                    Decimal(str(amount))
                    / Decimal(str(btc_price))
                    * Decimal(SATS_PER_BTC)
                ),
            )
    except (InvalidOperation, ValueError, TypeError) as err:
        raise HomeAssistantError(f"Invalid amount '{amount}' for unit '{unit}': {err}") from err

    return sats
