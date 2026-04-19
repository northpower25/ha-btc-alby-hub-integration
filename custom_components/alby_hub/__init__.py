"""Alby Hub integration."""

from __future__ import annotations

import logging
from dataclasses import replace

from homeassistant.components import frontend
from homeassistant.components.lovelace.const import (
    CONF_ICON,
    CONF_REQUIRE_ADMIN,
    CONF_SHOW_IN_SIDEBAR,
    CONF_TITLE,
    CONF_URL_PATH,
    LOVELACE_DATA,
)
from homeassistant.components.lovelace.dashboard import DashboardsCollection, LovelaceStorage
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlbyHubApiClient
from .const import (
    CONF_HUB_URL,
    CONF_MODE,
    CONF_NETWORK_API_BASE,
    CONF_NETWORK_PROVIDER,
    CONF_NWC_URI,
    CONF_PRICE_CURRENCY,
    CONF_PRICE_PROVIDER,
    CONF_RELAY_OVERRIDE,
    DASHBOARD_VERSION,
    DEFAULT_NETWORK_PROVIDER,
    DEFAULT_PRICE_CURRENCY,
    DEFAULT_PRICE_PROVIDER,
    DOMAIN,
    MODE_EXPERT,
)
from .coordinator import AlbyHubDataUpdateCoordinator
from .helpers import AlbyHubRuntime
from .nwc import parse_nwc_connection_uri
from .services import async_setup_services, async_unload_services

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.TEXT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
]
_DASHBOARD_URL = "alby-hub"
_DASHBOARD_ICON = "mdi:lightning-bolt"
_DASHBOARD_TITLE = "Alby Hub"
_DASHBOARD_REQUIRE_ADMIN = False
_DASHBOARD_SHOW_IN_SIDEBAR = True


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration from YAML (unused)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alby Hub from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Merge options over data so reconfiguration via the gear icon takes effect
    merged = dict(entry.data)
    merged.update(entry.options)

    nwc_info = parse_nwc_connection_uri(merged[CONF_NWC_URI])
    relay_override = merged.get(CONF_RELAY_OVERRIDE)
    if relay_override:
        nwc_info = replace(nwc_info, relay=relay_override)

    mode = merged[CONF_MODE]
    session = async_get_clientsession(hass)
    api_client = None
    if mode == MODE_EXPERT:
        hub_url = merged.get(CONF_HUB_URL)
        if hub_url:
            api_client = AlbyHubApiClient(session, hub_url)

    coordinator = AlbyHubDataUpdateCoordinator(
        hass,
        mode=mode,
        nwc_info=nwc_info,
        api_client=api_client,
        session=session,
        price_provider=merged.get(CONF_PRICE_PROVIDER, DEFAULT_PRICE_PROVIDER),
        price_currency=merged.get(CONF_PRICE_CURRENCY, DEFAULT_PRICE_CURRENCY),
        network_provider=merged.get(CONF_NETWORK_PROVIDER, DEFAULT_NETWORK_PROVIDER),
        network_api_base=merged.get(CONF_NETWORK_API_BASE),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = AlbyHubRuntime(
        coordinator=coordinator,
        api_client=api_client,
        nwc_info=nwc_info,
        session=session,
    )

    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_ensure_dashboard(hass)

    # Reload the entry whenever options are saved via the gear icon
    entry.async_on_unload(entry.add_update_listener(_async_options_update_listener))

    return True


async def _async_options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    if not hass.data[DOMAIN]:
        await async_unload_services(hass)

    return unload_ok


async def _async_ensure_dashboard(hass: HomeAssistant) -> None:
    """Create or update the Alby Hub dashboard with versioned starter cards."""
    if LOVELACE_DATA not in hass.data:
        return

    # If dashboard already registered: check version and update content if stale
    if _DASHBOARD_URL in hass.data[LOVELACE_DATA].dashboards:
        existing = hass.data[LOVELACE_DATA].dashboards[_DASHBOARD_URL]
        try:
            current_config = await existing.async_load(False)
            if current_config.get("_version") != DASHBOARD_VERSION:
                _LOGGER.debug(
                    "Alby Hub dashboard version mismatch (%s != %s) – updating",
                    current_config.get("_version"),
                    DASHBOARD_VERSION,
                )
                await existing.async_save(_default_dashboard_config())
        except Exception:  # noqa: BLE001
            # Dashboard not yet saved or load failed – save the default
            try:
                await existing.async_save(_default_dashboard_config())
            except Exception:  # noqa: BLE001
                pass
        return

    dashboards_collection = DashboardsCollection(hass)
    await dashboards_collection.async_load()
    for item in dashboards_collection.async_items():
        if item.get(CONF_URL_PATH) == _DASHBOARD_URL:
            return

    try:
        item = await dashboards_collection.async_create_item(
            {
                CONF_ICON: _DASHBOARD_ICON,
                CONF_TITLE: _DASHBOARD_TITLE,
                CONF_URL_PATH: _DASHBOARD_URL,
                CONF_REQUIRE_ADMIN: _DASHBOARD_REQUIRE_ADMIN,
                CONF_SHOW_IN_SIDEBAR: _DASHBOARD_SHOW_IN_SIDEBAR,
            }
        )
    except (HomeAssistantError, ValueError):
        return

    lovelace_config = LovelaceStorage(hass, item)
    await lovelace_config.async_save(_default_dashboard_config())
    hass.data[LOVELACE_DATA].dashboards[_DASHBOARD_URL] = lovelace_config

    frontend.async_register_built_in_panel(
        hass,
        "lovelace",
        frontend_url_path=_DASHBOARD_URL,
        require_admin=_DASHBOARD_REQUIRE_ADMIN,
        show_in_sidebar=_DASHBOARD_SHOW_IN_SIDEBAR,
        sidebar_title=_DASHBOARD_TITLE,
        sidebar_icon=_DASHBOARD_ICON,
        config={"mode": "storage"},
        update=False,
    )


def _default_dashboard_config() -> dict:
    """Return versioned Lovelace dashboard config for Alby Hub."""
    return {
        "title": "Alby Hub",
        "_version": DASHBOARD_VERSION,
        "views": [
            {
                "title": "Receive",
                "path": "receive",
                "icon": "mdi:arrow-bottom-left",
                "cards": [
                    # ── Create a new BOLT11 invoice ──────────────────────────
                    {
                        "type": "entities",
                        "title": "Create Invoice",
                        "show_header_toggle": False,
                        "entities": [
                            {
                                "entity": "number.alby_hub_invoice_amount",
                                "name": "Amount",
                            },
                            {
                                "entity": "select.alby_hub_invoice_amount_unit",
                                "name": "Unit (SAT / BTC / Fiat)",
                            },
                            {
                                "entity": "button.alby_hub_create_invoice_btn",
                                "name": "Create Invoice",
                            },
                        ],
                    },
                    # ── Show generated BOLT11 invoice + QR ───────────────────
                    {
                        "type": "markdown",
                        "title": "BOLT11 Invoice & QR Code",
                        "content": (
                            "{% set inv = states('text.alby_hub_last_invoice') %}\n"
                            "{% if inv and inv not in ('unavailable', 'unknown', '') %}\n"
                            "**Invoice:**\n"
                            "```\n{{ inv }}\n```\n\n"
                            "[![QR Code]"
                            "(https://api.qrserver.com/v1/create-qr-code/"
                            "?data=lightning:{{ inv }}&size=300x300&margin=10)]"
                            "(https://api.qrserver.com/v1/create-qr-code/"
                            "?data=lightning:{{ inv }}&size=300x300&margin=10)  \n"
                            "*(Scan or copy the invoice above)*\n"
                            "{% else %}\n"
                            "No invoice yet. Set the amount and unit above, then press "
                            "**Create Invoice**.\n"
                            "{% endif %}"
                        ),
                    },
                    # ── Lightning address & BOLT12 offer QR ──────────────────
                    {
                        "type": "entities",
                        "title": "Lightning Address",
                        "show_header_toggle": False,
                        "entities": ["sensor.alby_hub_lightning_address"],
                    },
                    {
                        "type": "markdown",
                        "title": "Lightning Address QR (receive without fixed amount)",
                        "content": (
                            "{% set addr = states('sensor.alby_hub_lightning_address') %}\n"
                            "{% if addr and addr not in ('unavailable', 'unknown', '') %}\n"
                            "[![QR Code]"
                            "(https://api.qrserver.com/v1/create-qr-code/"
                            "?data=lightning:{{ addr }}&size=250x250&margin=10)]"
                            "(https://api.qrserver.com/v1/create-qr-code/"
                            "?data=lightning:{{ addr }}&size=250x250&margin=10)  \n"
                            "**{{ addr }}**\n"
                            "{% else %}\n"
                            "Lightning address not available.\n"
                            "{% endif %}"
                        ),
                    },
                    # ── Balance summary ───────────────────────────────────────
                    {
                        "type": "entities",
                        "title": "Balance",
                        "show_header_toggle": False,
                        "entities": [
                            "sensor.alby_hub_balance_lightning",
                            "sensor.alby_hub_balance_onchain",
                        ],
                    },
                ],
            },
            {
                "title": "Send",
                "path": "send",
                "icon": "mdi:arrow-top-right",
                "cards": [
                    # ── Invoice / address input ───────────────────────────────
                    {
                        "type": "entities",
                        "title": "Payment",
                        "show_header_toggle": False,
                        "entities": [
                            {
                                "entity": "text.alby_hub_invoice_input",
                                "name": "BOLT11 Invoice / Lightning Address",
                            }
                        ],
                    },
                    {
                        "type": "markdown",
                        "title": "How to pay",
                        "content": (
                            "**Option 1 – Paste:**  \n"
                            "Copy a BOLT11 invoice (or Lightning address) and paste it "
                            "into the field above.\n\n"
                            "**Option 2 – QR scan (HA Companion App):**  \n"
                            "Tap the QR-code icon next to the input field to scan a "
                            "Lightning invoice with your phone camera.\n\n"
                            "Then press **Send Payment** below."
                        ),
                    },
                    # ── Send button ───────────────────────────────────────────
                    {
                        "type": "button",
                        "name": "Send Payment",
                        "icon": "mdi:send",
                        "tap_action": {
                            "action": "call-service",
                            "service": "alby_hub.send_payment",
                        },
                    },
                    # ── Balance summary ───────────────────────────────────────
                    {
                        "type": "entities",
                        "title": "Balance",
                        "show_header_toggle": False,
                        "entities": [
                            "sensor.alby_hub_balance_lightning",
                            "sensor.alby_hub_balance_onchain",
                        ],
                    },
                ],
            },
            {
                "title": "Network",
                "path": "network",
                "icon": "mdi:bitcoin",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Bitcoin Market & Network",
                        "show_header_toggle": False,
                        "entities": [
                            "sensor.alby_hub_bitcoin_price",
                            "sensor.alby_hub_bitcoin_block_height",
                            "sensor.alby_hub_bitcoin_hashrate",
                            "sensor.alby_hub_blocks_until_halving",
                            "sensor.alby_hub_next_halving_eta",
                        ],
                    },
                ],
            },
        ],
    }
