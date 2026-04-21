"""Service registration for Alby Hub."""

from __future__ import annotations

import logging
from decimal import Decimal

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
    SERVICE_DELETE_SCHEDULED_PAYMENT,
    SERVICE_LIST_SCHEDULED_PAYMENTS,
    SERVICE_LIST_TRANSACTIONS,
    SERVICE_SCHEDULE_PAYMENT,
    SERVICE_SEND_PAYMENT,
    TEXT_KEY_INVOICE_INPUT,
)
from .helpers import AlbyHubRuntime
from .nwc_client import async_nwc_request
from .recurring_payments import VALID_FREQUENCIES, get_scheduler

_LOGGER = logging.getLogger(__name__)
_MSATS_PER_SAT = 1000

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
        vol.Optional("amount_sat"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("amount_btc"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Optional("amount_fiat"): vol.All(vol.Coerce(float), vol.Range(min=0)),
        vol.Optional("fiat_currency"): cv.string,
    }
)

SERVICE_LIST_TRANSACTIONS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("limit", default=50): vol.All(vol.Coerce(int), vol.Range(min=1, max=500)),
    }
)

SERVICE_SCHEDULE_PAYMENT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("recipient"): cv.string,
        vol.Required("amount_sat"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("label"): cv.string,
        vol.Optional("memo"): cv.string,
        vol.Required("frequency"): vol.In(list(VALID_FREQUENCIES)),
        vol.Optional("hour", default=8): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Optional("minute", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
        vol.Optional("day_of_week", default=0): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
        vol.Optional("day_of_month", default=1): vol.All(vol.Coerce(int), vol.Range(min=1, max=28)),
        vol.Optional("start_date"): cv.string,
        vol.Optional("end_date"): cv.string,
    }
)

SERVICE_LIST_SCHEDULED_PAYMENTS_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
    }
)

SERVICE_DELETE_SCHEDULED_PAYMENT_SCHEMA = vol.Schema(
    {
        vol.Required("schedule_id"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_INVOICE):
        return
    async def handle_create_invoice(call: ServiceCall) -> ServiceResponse:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))

        amount_sat = _resolve_amount_sat(call.data, runtime)

        mode = runtime.coordinator.data.get("mode")
        invoice_str = ""

        if mode == MODE_EXPERT and runtime.api_client is not None:
            try:
                result = await runtime.api_client.create_invoice(
                    amount_sat=amount_sat,
                    memo=call.data.get("memo"),
                    expiry_seconds=call.data.get("expiry_seconds"),
                )
                _LOGGER.debug("Invoice created successfully: %s", result)
            except AlbyHubApiError as err:
                raise HomeAssistantError(f"Failed to create invoice: {err}") from err
            invoice_str = result.get("payment_request") or result.get("invoice") or ""
        else:
            # Cloud mode: use NWC make_invoice
            params: dict = {"amount": amount_sat * _MSATS_PER_SAT}
            if memo := call.data.get("memo"):
                params["description"] = memo
            if expiry := call.data.get("expiry_seconds"):
                params["expiry"] = expiry
            result = await async_nwc_request(
                runtime.session, runtime.nwc_info, "make_invoice", params
            )
            if result is None or result.get("error"):
                raise HomeAssistantError(
                    f"NWC make_invoice failed: {result.get('error') if result else 'no response'}"
                )
            inv_result = result.get("result") or {}
            invoice_str = inv_result.get("invoice") or inv_result.get("payment_request") or ""
            _LOGGER.debug("NWC invoice created: %s…", invoice_str[:20] if invoice_str else "")

        if invoice_str:
            if runtime.last_invoice_entity is not None:
                await runtime.last_invoice_entity.async_set_invoice(invoice_str)

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

        payment_request = call.data.get("payment_request") or ""
        if not payment_request:
            invoice_input_entity = runtime.text_entities.get(TEXT_KEY_INVOICE_INPUT)
            if invoice_input_entity is not None:
                payment_request = invoice_input_entity.native_value or ""
        if not payment_request:
            raise ServiceValidationError(
                "No payment_request provided and invoice_input entity is empty"
            )

        mode = runtime.coordinator.data.get("mode")

        if mode == MODE_EXPERT and runtime.api_client is not None:
            try:
                result = await runtime.api_client.send_payment(payment_request)
                _LOGGER.debug("Payment sent successfully: %s", result)
            except AlbyHubApiError as err:
                raise HomeAssistantError(f"Failed to send payment: {err}") from err
        else:
            # Cloud mode: use NWC pay_invoice
            result = await async_nwc_request(
                runtime.session,
                runtime.nwc_info,
                "pay_invoice",
                {"invoice": payment_request},
            )
            if result is None or result.get("error"):
                raise HomeAssistantError(
                    f"NWC pay_invoice failed: {result.get('error') if result else 'no response'}"
                )
            result = result.get("result") or {}
            _LOGGER.debug("NWC payment sent: %s", result)

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

    async def handle_list_transactions(call: ServiceCall) -> ServiceResponse:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        limit = call.data.get("limit", 50)
        mode = runtime.coordinator.data.get("mode")
        raw_txs: list = []

        if mode == MODE_EXPERT and runtime.api_client is not None:
            try:
                result = await runtime.api_client.list_transactions(limit=limit)
                raw_txs = result if isinstance(result, list) else (
                    result.get("transactions") or result.get("data") or []
                )
            except AlbyHubApiError as err:
                raise HomeAssistantError(f"Failed to list transactions: {err}") from err
        else:
            result = await async_nwc_request(
                runtime.session,
                runtime.nwc_info,
                "list_transactions",
                {"limit": limit, "unpaid": False},
            )
            if result and result.get("error") is None:
                tx_result = result.get("result") or {}
                raw_txs = tx_result.get("transactions") or []
            else:
                raise HomeAssistantError(
                    f"NWC list_transactions failed: {result.get('error') if result else 'no response'}"
                )

        from .coordinator import _normalize_transactions  # noqa: PLC0415
        normalized = _normalize_transactions(raw_txs)
        return {"transactions": normalized, "count": len(normalized)}

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_TRANSACTIONS,
        handle_list_transactions,
        schema=SERVICE_LIST_TRANSACTIONS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def handle_schedule_payment(call: ServiceCall) -> ServiceResponse:
        scheduler = get_scheduler(hass)
        if scheduler is None:
            raise HomeAssistantError("Scheduler not initialised")
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID) or _default_entry_id(hass)
        try:
            schedule = await scheduler.async_create(entry_id, dict(call.data))
        except (ValueError, KeyError) as err:
            raise ServiceValidationError(str(err)) from err
        return {"schedule": schedule}

    hass.services.async_register(
        DOMAIN,
        SERVICE_SCHEDULE_PAYMENT,
        handle_schedule_payment,
        schema=SERVICE_SCHEDULE_PAYMENT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_list_scheduled_payments(call: ServiceCall) -> ServiceResponse:
        scheduler = get_scheduler(hass)
        if scheduler is None:
            return {"schedules": [], "count": 0}
        entry_id = call.data.get(ATTR_CONFIG_ENTRY_ID)
        schedules = scheduler.list_schedules(entry_id)
        return {"schedules": schedules, "count": len(schedules)}

    hass.services.async_register(
        DOMAIN,
        SERVICE_LIST_SCHEDULED_PAYMENTS,
        handle_list_scheduled_payments,
        schema=SERVICE_LIST_SCHEDULED_PAYMENTS_SCHEMA,
        supports_response=SupportsResponse.ONLY,
    )

    async def handle_delete_scheduled_payment(call: ServiceCall) -> None:
        scheduler = get_scheduler(hass)
        if scheduler is None:
            raise HomeAssistantError("Scheduler not initialised")
        deleted = await scheduler.async_delete(call.data["schedule_id"])
        if not deleted:
            raise ServiceValidationError(
                f"Schedule '{call.data['schedule_id']}' not found"
            )

    hass.services.async_register(
        DOMAIN,
        SERVICE_DELETE_SCHEDULED_PAYMENT,
        handle_delete_scheduled_payment,
        schema=SERVICE_DELETE_SCHEDULED_PAYMENT_SCHEMA,
    )


async def async_unload_services(hass: HomeAssistant) -> None:
    """Unload integration services when no entries remain."""
    for svc in (
        SERVICE_CREATE_INVOICE,
        SERVICE_SEND_PAYMENT,
        SERVICE_LIST_TRANSACTIONS,
        SERVICE_SCHEDULE_PAYMENT,
        SERVICE_LIST_SCHEDULED_PAYMENTS,
        SERVICE_DELETE_SCHEDULED_PAYMENT,
    ):
        hass.services.async_remove(DOMAIN, svc)


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


def _resolve_amount_sat(data: dict, runtime: AlbyHubRuntime) -> int:
    """Resolve invoice amount in satoshis from service call parameters."""
    if "amount_sat" in data:
        return int(data["amount_sat"])

    if "amount_btc" in data:
        raw_sat = int(Decimal(str(data["amount_btc"])) * Decimal(SATS_PER_BTC))
        if raw_sat < 1:
            raise ServiceValidationError(
                f"amount_btc too small: {data['amount_btc']} BTC converts to {raw_sat} sat (minimum 1 sat)."
            )
        return raw_sat

    if "amount_fiat" in data:
        btc_price = runtime.coordinator.data.get("bitcoin_price")
        if not btc_price or float(btc_price) <= 0:
            raise ServiceValidationError(
                "Cannot convert fiat to sats: Bitcoin price not available. "
                "Check network/price provider configuration."
            )
        raw_sat = int(
            Decimal(str(data["amount_fiat"])) / Decimal(str(btc_price)) * Decimal(SATS_PER_BTC)
        )
        if raw_sat < 1:
            raise ServiceValidationError(
                f"amount_fiat too small: {data['amount_fiat']} converts to {raw_sat} sat (minimum 1 sat). "
                "Use a larger amount."
            )
        return raw_sat

    raise ServiceValidationError(
        "One of amount_sat, amount_btc, or amount_fiat must be provided."
    )


def _default_entry_id(hass: HomeAssistant) -> str | None:
    runtimes: dict = hass.data.get(DOMAIN, {})
    return next(iter(runtimes), None)
