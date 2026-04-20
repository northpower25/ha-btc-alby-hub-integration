"""Helpers for runtime access."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from aiohttp import ClientSession
from homeassistant.core import HomeAssistant

from .api import AlbyHubApiClient
from .const import DOMAIN
from .coordinator import AlbyHubDataUpdateCoordinator
from .nwc import NwcConnectionInfo

if TYPE_CHECKING:
    from .button import AlbyHubCreateInvoiceButton
    from .number import AlbyHubInvoiceAmountNumber
    from .select import AlbyHubInvoiceAmountUnitSelect
    from .sensor import AlbyHubLastInvoiceSensor
    from .text import AlbyHubTextEntity


@dataclass(slots=False)  # slots=False: dict fields are populated after __init__ via platform setup
class AlbyHubRuntime:
    """Runtime objects bound to one config entry."""

    coordinator: AlbyHubDataUpdateCoordinator
    api_client: AlbyHubApiClient | None
    nwc_info: NwcConnectionInfo
    session: ClientSession
    text_entities: dict[str, "AlbyHubTextEntity"] = field(default_factory=dict)
    number_entities: dict[str, "AlbyHubInvoiceAmountNumber"] = field(default_factory=dict)
    select_entities: dict[str, "AlbyHubInvoiceAmountUnitSelect"] = field(default_factory=dict)
    last_invoice_entity: "AlbyHubLastInvoiceSensor | None" = field(default=None)


def get_runtime(hass: HomeAssistant, entry_id: str) -> AlbyHubRuntime:
    """Return runtime for config entry."""
    return hass.data[DOMAIN][entry_id]
