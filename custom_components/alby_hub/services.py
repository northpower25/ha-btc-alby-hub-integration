"""Service registration for Alby Hub."""

from __future__ import annotations

import asyncio
import logging
import re
from decimal import Decimal
from urllib.parse import quote

import voluptuous as vol

from aiohttp import ClientError, ClientTimeout
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
    SERVICE_NOSTR_LIST_MESSAGES,
    SERVICE_NOSTR_SEND_BOT_MESSAGE,
    SERVICE_NOSTR_SEND_TEST_MESSAGE,
    SERVICE_RUN_SCHEDULED_PAYMENT_NOW,
    SERVICE_LIST_TRANSACTIONS,
    SERVICE_SCHEDULE_PAYMENT,
    SERVICE_SEND_PAYMENT,
    SERVICE_UPDATE_SCHEDULED_PAYMENT,
    TEXT_KEY_INVOICE_INPUT,
)
from .helpers import AlbyHubRuntime, is_lightning_address
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
        vol.Optional("memo"): cv.string,
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

SERVICE_UPDATE_SCHEDULED_PAYMENT_SCHEMA = vol.Schema(
    {
        vol.Required("schedule_id"): cv.string,
        vol.Optional("recipient"): cv.string,
        vol.Optional("amount_sat"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("label"): cv.string,
        vol.Optional("memo"): cv.string,
        vol.Optional("frequency"): vol.In(list(VALID_FREQUENCIES)),
        vol.Optional("hour"): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
        vol.Optional("minute"): vol.All(vol.Coerce(int), vol.Range(min=0, max=59)),
        vol.Optional("day_of_week"): vol.All(vol.Coerce(int), vol.Range(min=0, max=6)),
        vol.Optional("day_of_month"): vol.All(vol.Coerce(int), vol.Range(min=1, max=28)),
        vol.Optional("start_date"): cv.string,
        vol.Optional("end_date"): vol.Any(cv.string, None),
        vol.Optional("enabled"): cv.boolean,
    }
)

SERVICE_RUN_SCHEDULED_PAYMENT_NOW_SCHEMA = vol.Schema(
    {
        vol.Required("schedule_id"): cv.string,
    }
)

SERVICE_NOSTR_SEND_BOT_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("target_npub"): cv.string,
        vol.Required("message"): cv.string,
    }
)

SERVICE_NOSTR_SEND_TEST_MESSAGE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("nsec"): cv.string,
        vol.Required("message"): cv.string,
    }
)

SERVICE_NOSTR_LIST_MESSAGES_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Optional("limit", default=100): vol.All(vol.Coerce(int), vol.Range(min=1, max=250)),
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

        if invoice_str and runtime.last_invoice_entity is not None:
            await runtime.last_invoice_entity.async_set_invoice(
                invoice_str,
                amount_sat=amount_sat,
                memo=call.data.get("memo"),
            )

        return {
            "payment_request": invoice_str,
            "amount_sat": amount_sat,
            "memo": call.data.get("memo"),
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
        amount_sat: int | None = None
        if {"amount_sat", "amount_btc", "amount_fiat"} & set(call.data):
            amount_sat = _resolve_amount_sat(call.data, runtime)
        memo = call.data.get("memo")
        is_ln_address = is_lightning_address(payment_request)
        if is_ln_address and amount_sat is None:
            raise ServiceValidationError(
                "Lightning address payments require amount_sat, amount_btc, or amount_fiat."
            )
        resolved_payment_request = await _resolve_payment_request(
            runtime, payment_request, amount_sat, memo
        )
        send_amount = None if is_ln_address else amount_sat

        if mode == MODE_EXPERT and runtime.api_client is not None:
            try:
                result = await runtime.api_client.send_payment(
                    resolved_payment_request,
                    amount_sat=send_amount,
                    memo=memo,
                )
                _LOGGER.debug("Payment sent successfully: %s", result)
            except AlbyHubApiError as err:
                raise HomeAssistantError(f"Failed to send payment: {err}") from err
        else:
            # Cloud mode: use NWC pay_invoice
            params: dict[str, str | int] = {"invoice": resolved_payment_request}
            if send_amount is not None:
                params["amount"] = send_amount * _MSATS_PER_SAT
            if memo:
                params["description"] = memo
            result = await async_nwc_request(
                runtime.session,
                runtime.nwc_info,
                "pay_invoice",
                params,
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
                {"limit": limit, "unpaid": True},
            )
            if result and result.get("error") is None:
                tx_result = result.get("result") or {}
                raw_txs = (
                    tx_result
                    if isinstance(tx_result, list)
                    else (tx_result.get("transactions") or tx_result.get("data") or [])
                )
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

    async def handle_update_scheduled_payment(call: ServiceCall) -> ServiceResponse:
        scheduler = get_scheduler(hass)
        if scheduler is None:
            raise HomeAssistantError("Scheduler not initialised")
        schedule_id = call.data["schedule_id"]
        updates = {k: v for k, v in call.data.items() if k != "schedule_id"}
        updated = await scheduler.async_update(schedule_id, updates)
        if updated is None:
            raise ServiceValidationError(f"Schedule '{schedule_id}' not found")
        return {"schedule": updated}

    hass.services.async_register(
        DOMAIN,
        SERVICE_UPDATE_SCHEDULED_PAYMENT,
        handle_update_scheduled_payment,
        schema=SERVICE_UPDATE_SCHEDULED_PAYMENT_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_run_scheduled_payment_now(call: ServiceCall) -> ServiceResponse:
        scheduler = get_scheduler(hass)
        if scheduler is None:
            raise HomeAssistantError("Scheduler not initialised")
        schedule = await scheduler.async_run_now(call.data["schedule_id"])
        if schedule is None:
            raise ServiceValidationError(f"Schedule '{call.data['schedule_id']}' not found")
        return {"schedule": schedule}

    hass.services.async_register(
        DOMAIN,
        SERVICE_RUN_SCHEDULED_PAYMENT_NOW,
        handle_run_scheduled_payment_now,
        schema=SERVICE_RUN_SCHEDULED_PAYMENT_NOW_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_nostr_send_bot_message(call: ServiceCall) -> ServiceResponse:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        manager = runtime.nostr_bot_manager
        if manager is None:
            raise ServiceValidationError("Nostr bot/client is not enabled for this entry")
        target_npub = call.data["target_npub"].strip()
        message = call.data["message"].strip()
        if not target_npub or not message:
            raise ServiceValidationError("target_npub and message are required")
        try:
            event_id = await manager.async_send_bot_message(target_npub, message)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except (ClientError, asyncio.TimeoutError, RuntimeError) as err:
            raise HomeAssistantError(f"Nostr bot send failed: {err}") from err
        return {"ok": True, "event_id": event_id}

    hass.services.async_register(
        DOMAIN,
        SERVICE_NOSTR_SEND_BOT_MESSAGE,
        handle_nostr_send_bot_message,
        schema=SERVICE_NOSTR_SEND_BOT_MESSAGE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_nostr_send_test_message(call: ServiceCall) -> ServiceResponse:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        manager = runtime.nostr_bot_manager
        if manager is None:
            raise ServiceValidationError("Nostr bot/client is not enabled for this entry")
        nsec = call.data["nsec"].strip()
        message = call.data["message"].strip()
        if not nsec or not message:
            raise ServiceValidationError("nsec and message are required")
        try:
            event_id = await manager.async_send_test_message(nsec, message)
        except ValueError as err:
            raise ServiceValidationError(str(err)) from err
        except (ClientError, asyncio.TimeoutError, RuntimeError) as err:
            raise HomeAssistantError(f"Nostr test send failed: {err}") from err
        return {"ok": True, "event_id": event_id}

    hass.services.async_register(
        DOMAIN,
        SERVICE_NOSTR_SEND_TEST_MESSAGE,
        handle_nostr_send_test_message,
        schema=SERVICE_NOSTR_SEND_TEST_MESSAGE_SCHEMA,
        supports_response=SupportsResponse.OPTIONAL,
    )

    async def handle_nostr_list_messages(call: ServiceCall) -> ServiceResponse:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        manager = runtime.nostr_bot_manager
        if manager is None:
            return {
                "enabled": False,
                "messages": [],
                "count": 0,
                "bot_npub": "",
                "webhook_url": "",
                "encryption_mode": "",
                "relay_listener_active": False,
            }
        limit = int(call.data.get("limit", 100))
        messages = manager.list_messages(limit=limit)
        return {
            "enabled": True,
            "messages": messages,
            "count": len(messages),
            "bot_npub": manager.bot_npub,
            "webhook_url": manager.webhook_url,
            "encryption_mode": manager.encryption_mode,
            "relay_listener_active": runtime.nostr_relay_listener is not None,
        }

    hass.services.async_register(
        DOMAIN,
        SERVICE_NOSTR_LIST_MESSAGES,
        handle_nostr_list_messages,
        schema=SERVICE_NOSTR_LIST_MESSAGES_SCHEMA,
        supports_response=SupportsResponse.ONLY,
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
        SERVICE_UPDATE_SCHEDULED_PAYMENT,
        SERVICE_RUN_SCHEDULED_PAYMENT_NOW,
        SERVICE_NOSTR_SEND_BOT_MESSAGE,
        SERVICE_NOSTR_SEND_TEST_MESSAGE,
        SERVICE_NOSTR_LIST_MESSAGES,
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


async def _resolve_payment_request(
    runtime: AlbyHubRuntime,
    payment_request: str,
    amount_sat: int | None,
    memo: str | None,
) -> str:
    """Resolve Lightning addresses to BOLT11 invoices.

    For plain BOLT11 strings the input is returned unchanged.
    For Lightning addresses the LNURL-pay flow is executed and the
    resulting BOLT11 invoice is returned.  ``amount_sat`` must be
    non-None when ``payment_request`` is a Lightning address; callers
    are responsible for validating this before the call.
    """
    target = payment_request.strip()
    if not is_lightning_address(target):
        return target
    # amount_sat is guaranteed non-None here: handle_send_payment validates
    # this before calling _resolve_payment_request.
    return await _fetch_lnurl_invoice(runtime, target, int(amount_sat), memo)  # type: ignore[arg-type]


async def _fetch_lnurl_invoice(
    runtime: AlbyHubRuntime,
    lightning_address: str,
    amount_sat: int,
    memo: str | None,
) -> str:
    try:
        localpart, domain = lightning_address.split("@", 1)
    except ValueError as err:
        raise ServiceValidationError("Invalid Lightning address format") from err
    if not localpart or not domain:
        raise ServiceValidationError("Invalid Lightning address format")
    domain = domain.strip().lower()
    if not _is_valid_lightning_domain(domain):
        raise ServiceValidationError("Invalid Lightning address domain")

    msat_amount = amount_sat * _MSATS_PER_SAT
    lnurlp_url = f"https://{domain}/.well-known/lnurlp/{quote(localpart, safe='')}"
    timeout = ClientTimeout(total=10)

    async with runtime.session.get(lnurlp_url, timeout=timeout) as response:
        if response.status >= 400:
            raise HomeAssistantError(
                f"Failed to resolve Lightning address ({response.status}) at {domain}"
            )
        metadata = await response.json(content_type=None)

    if not isinstance(metadata, dict):
        raise HomeAssistantError("Lightning address metadata response was invalid")

    callback_url = metadata.get("callback")
    min_sendable = metadata.get("minSendable")
    max_sendable = metadata.get("maxSendable")
    if not isinstance(callback_url, str) or not callback_url:
        raise HomeAssistantError("Lightning address metadata is missing callback URL")

    if isinstance(min_sendable, (int, float)) and msat_amount < int(min_sendable):
        raise ServiceValidationError(
            "Amount is below the minimum supported by this Lightning address"
        )
    if isinstance(max_sendable, (int, float)) and msat_amount > int(max_sendable):
        raise ServiceValidationError(
            "Amount is above the maximum supported by this Lightning address"
        )

    params: dict[str, int | str] = {"amount": msat_amount}
    comment_allowed = metadata.get("commentAllowed")
    if memo and isinstance(comment_allowed, (int, float)) and int(comment_allowed) > 0:
        max_comment = int(comment_allowed)
        if len(memo) > max_comment:
            _LOGGER.warning(
                "Lightning address memo truncated from %d to %d characters",
                len(memo),
                max_comment,
            )
        params["comment"] = memo[:max_comment]

    async with runtime.session.get(callback_url, params=params, timeout=timeout) as response:
        if response.status >= 400:
            raise HomeAssistantError(
                f"Lightning address callback failed with HTTP {response.status}"
            )
        callback_data = await response.json(content_type=None)

    if not isinstance(callback_data, dict):
        raise HomeAssistantError("Lightning address callback response was invalid")
    if callback_data.get("status") == "ERROR":
        reason = callback_data.get("reason") or "unknown reason"
        raise HomeAssistantError(f"Lightning address callback error: {reason}")

    invoice = callback_data.get("pr") or callback_data.get("payment_request")
    if not isinstance(invoice, str) or not invoice.strip():
        raise HomeAssistantError("Lightning address callback did not return a BOLT11 invoice")
    return invoice.strip()


def _is_valid_lightning_domain(domain: str) -> bool:
    return bool(
        re.fullmatch(
            r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?(?:\.[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?)*",
            domain,
        )
    )
