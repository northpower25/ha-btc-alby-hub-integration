"""Service registration for Alby Hub."""

from __future__ import annotations

import logging

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import AlbyHubApiError
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    DOMAIN,
    MODE_EXPERT,
    SATS_PER_BTC,
    SERVICE_CREATE_INVOICE,
    SERVICE_SEND_PAYMENT,
    TEXT_KEY_INVOICE_INPUT,
    TEXT_KEY_LAST_INVOICE,
)
from .helpers import AlbyHubRuntime

_LOGGER = logging.getLogger(__name__)

SERVICE_CREATE_INVOICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("amount_sat"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("amount_btc"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Optional("amount_fiat"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Optional("fiat_currency"): cv.string,
        vol.Optional("memo"): cv.string,
        vol.Optional("expiry_seconds"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

SERVICE_SEND_PAYMENT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("payment_request"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_INVOICE):
        return

    async def handle_create_invoice(call: ServiceCall) -> ServiceResponse:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        _assert_expert_mode(runtime)
        if runtime.api_client is None:
            raise ServiceValidationError("Expert mode API client is unavailable")

        amount_sat = _resolve_amount_sat(call.data, runtime)

        try:
            result = await runtime.api_client.create_invoice(
                amount_sat=amount_sat,
                memo=call.data.get("memo"),
                expiry_seconds=call.data.get("expiry_seconds"),
            )
            _LOGGER.debug("Invoice created successfully: %s", result)
        except AlbyHubApiError as err:
            raise HomeAssistantError(f"Failed to create invoice: {err}") from err

        invoice_str: str = result.get("payment_request") or result.get("invoice") or ""
        if invoice_str:
            last_invoice_entity = runtime.text_entities.get(TEXT_KEY_LAST_INVOICE)
            if last_invoice_entity is not None:
                await last_invoice_entity.async_set_value(invoice_str)

        return {
            "payment_request": invoice_str,
            "amount_sat": amount_sat,
            "qr_url": (
                f"https://api.qrserver.com/v1/create-qr-code/?data=lightning:{invoice_str}&size=300x300"
                if invoice_str
                else ""
            ),
        }

    async def handle_send_payment(call: ServiceCall) -> ServiceResponse:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        _assert_expert_mode(runtime)
        if runtime.api_client is None:
            raise ServiceValidationError("Expert mode API client is unavailable")

        payment_request = call.data.get("payment_request") or ""
        if not payment_request:
            invoice_input_entity = runtime.text_entities.get(TEXT_KEY_INVOICE_INPUT)
            if invoice_input_entity is not None:
                payment_request = invoice_input_entity.native_value or ""
        if not payment_request:
            raise ServiceValidationError(
                "No payment_request provided and invoice_input entity is empty"
            )

        try:
            result = await runtime.api_client.send_payment(payment_request)
            _LOGGER.debug("Payment sent successfully: %s", result)
        except AlbyHubApiError as err:
            raise HomeAssistantError(f"Failed to send payment: {err}") from err

        # Clear invoice_input after successful payment
        invoice_input_entity = runtime.text_entities.get(TEXT_KEY_INVOICE_INPUT)
        if invoice_input_entity is not None:
            await invoice_input_entity.async_set_value("")

        return {"result": result}

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_INVOICE,
        handle_create_invoice,
        schema=SERVICE_CREATE_INVOICE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_PAYMENT,
        handle_send_payment,
        schema=SERVICE_SEND_PAYMENT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload integration services when no entries remain."""
    hass.services.async_remove(DOMAIN, SERVICE_CREATE_INVOICE)
    hass.services.async_remove(DOMAIN, SERVICE_SEND_PAYMENT)


def _resolve_runtime(hass: HomeAssistant, entry_id: str | None) -> AlbyHubRuntime:
    runtimes: dict[str, AlbyHubRuntime] = hass.data.get(DOMAIN, {})
    if not runtimes:
        raise ServiceValidationError("No Alby Hub config entries loaded")

    if entry_id:
        runtime = runtimes.get(entry_id)
        if runtime is None:
            raise ServiceValidationError(f"Unknown config entry id: {entry_id}")
        return runtime

    return next(iter(runtimes.values()))


def _assert_expert_mode(runtime: AlbyHubRuntime) -> None:
    if runtime.coordinator.data.get("mode") != MODE_EXPERT:
        raise ServiceValidationError(
            "This service currently requires expert mode with local API access"
        )


def _resolve_amount_sat(data: dict, runtime: AlbyHubRuntime) -> int:
    """Resolve invoice amount in satoshis from service call parameters."""
    if "amount_sat" in data:
        return int(data["amount_sat"])

    if "amount_btc" in data:
        return max(1, int(float(data["amount_btc"]) * SATS_PER_BTC))

    if "amount_fiat" in data:
        btc_price = runtime.coordinator.data.get("bitcoin_price")
        if not btc_price or float(btc_price) <= 0:
            raise ServiceValidationError(
                "Cannot convert fiat to sats: Bitcoin price not available. "
                "Check network/price provider configuration."
            )
        amount_fiat = float(data["amount_fiat"])
        return max(1, int((amount_fiat / float(btc_price)) * SATS_PER_BTC))

    raise ServiceValidationError(
        "One of amount_sat, amount_btc, or amount_fiat must be provided."
    )
