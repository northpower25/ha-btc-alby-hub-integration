"""Service registration for Alby Hub."""

from __future__ import annotations

import voluptuous as vol

from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv

from .api import AlbyHubApiError
from .const import (
    ATTR_CONFIG_ENTRY_ID,
    DOMAIN,
    MODE_EXPERT,
    SERVICE_CREATE_INVOICE,
    SERVICE_SEND_PAYMENT,
)
from .helpers import AlbyHubRuntime

SERVICE_CREATE_INVOICE_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("amount_sat"): vol.All(vol.Coerce(int), vol.Range(min=1)),
        vol.Optional("memo"): cv.string,
        vol.Optional("expiry_seconds"): vol.All(vol.Coerce(int), vol.Range(min=1)),
    }
)

SERVICE_SEND_PAYMENT_SCHEMA = vol.Schema(
    {
        vol.Optional(ATTR_CONFIG_ENTRY_ID): cv.string,
        vol.Required("payment_request"): cv.string,
    }
)


async def async_setup_services(hass: HomeAssistant) -> None:
    """Register integration services once."""
    if hass.services.has_service(DOMAIN, SERVICE_CREATE_INVOICE):
        return

    async def handle_create_invoice(call: ServiceCall) -> None:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        _assert_expert_mode(runtime)
        if runtime.api_client is None:
            raise ServiceValidationError("Expert mode API client is unavailable")

        try:
            await runtime.api_client.create_invoice(
                amount_sat=call.data["amount_sat"],
                memo=call.data.get("memo"),
                expiry_seconds=call.data.get("expiry_seconds"),
            )
        except AlbyHubApiError as err:
            raise HomeAssistantError(f"Failed to create invoice: {err}") from err

    async def handle_send_payment(call: ServiceCall) -> None:
        runtime = _resolve_runtime(hass, call.data.get(ATTR_CONFIG_ENTRY_ID))
        _assert_expert_mode(runtime)
        if runtime.api_client is None:
            raise ServiceValidationError("Expert mode API client is unavailable")

        try:
            await runtime.api_client.send_payment(call.data["payment_request"])
        except AlbyHubApiError as err:
            raise HomeAssistantError(f"Failed to send payment: {err}") from err

    hass.services.async_register(
        DOMAIN,
        SERVICE_CREATE_INVOICE,
        handle_create_invoice,
        schema=SERVICE_CREATE_INVOICE_SCHEMA,
    )
    hass.services.async_register(
        DOMAIN,
        SERVICE_SEND_PAYMENT,
        handle_send_payment,
        schema=SERVICE_SEND_PAYMENT_SCHEMA,
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
