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
    from .nostr_bot import AlbyHubNostrBotManager
    from .nostr_relay_listener import NostrRelayListener


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
    nostr_bot_manager: "AlbyHubNostrBotManager | None" = field(default=None)
    nostr_relay_listener: "NostrRelayListener | None" = field(default=None)


def get_runtime(hass: HomeAssistant, entry_id: str) -> AlbyHubRuntime:
    """Return runtime for config entry."""
    return hass.data[DOMAIN][entry_id]


def is_lightning_address(value: str) -> bool:
    """Return True when the value looks like a Lightning address user@domain."""
    normalized = str(value or "").strip().lower()
    return "@" in normalized and " " not in normalized and not normalized.startswith(
        ("lnbc", "lntb", "lnbcrt", "lnurl")
    )
