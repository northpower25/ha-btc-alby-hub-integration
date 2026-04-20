"""Alby Hub integration."""

from __future__ import annotations

import logging
import re
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
    CONF_CONNECTION_NAME,
    CONF_HUB_URL,
    CONF_MODE,
    CONF_NETWORK_API_BASE,
    CONF_NETWORK_PROVIDER,
    CONF_NWC_URI,
    CONF_PRICE_CURRENCY,
    CONF_PRICE_PROVIDER,
    CONF_RELAY_OVERRIDE,
    DASHBOARD_VERSION,
    DEFAULT_CONNECTION_NAME,
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
_DASHBOARD_ICON = "mdi:lightning-bolt"
_DASHBOARD_REQUIRE_ADMIN = False
_DASHBOARD_SHOW_IN_SIDEBAR = True


def _url_slug(name: str) -> str:
    """Convert a name to a URL-safe slug using hyphens (e.g. 'Alby Hub' → 'alby-hub')."""
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def _entity_slug(name: str) -> str:
    """Convert a name to an entity-ID-safe slug using underscores (e.g. 'Alby Hub' → 'alby_hub')."""
    return re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration from YAML (unused)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alby Hub from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    # Merge options over data so reconfiguration via the gear icon takes effect
    merged = dict(entry.data)
    merged.update(entry.options)

    connection_name = (
        merged.get(CONF_CONNECTION_NAME, "").strip() or DEFAULT_CONNECTION_NAME
    )

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
        entry_name=connection_name,
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
    await _async_ensure_dashboard(hass, entry.entry_id, connection_name)

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


async def _async_ensure_dashboard(
    hass: HomeAssistant, entry_id: str, connection_name: str
) -> None:
    """Create or update the Alby Hub dashboard for this config entry."""
    if LOVELACE_DATA not in hass.data:
        return

    dashboard_url = _url_slug(connection_name)
    dashboard_title = connection_name
    dashboard_config = _default_dashboard_config(connection_name)

    # If dashboard already registered: check version and update content if stale
    if dashboard_url in hass.data[LOVELACE_DATA].dashboards:
        existing = hass.data[LOVELACE_DATA].dashboards[dashboard_url]
        try:
            current_config = await existing.async_load(False)
            if current_config.get("_version") != DASHBOARD_VERSION:
                _LOGGER.debug(
                    "Alby Hub dashboard '%s' version mismatch (%s != %s) – updating",
                    dashboard_url,
                    current_config.get("_version"),
                    DASHBOARD_VERSION,
                )
                await existing.async_save(dashboard_config)
        except Exception:  # noqa: BLE001
            # Dashboard not yet saved or load failed – save the default
            try:
                await existing.async_save(dashboard_config)
            except Exception:  # noqa: BLE001
                pass
        return

    dashboards_collection = DashboardsCollection(hass)
    await dashboards_collection.async_load()
    for item in dashboards_collection.async_items():
        if item.get(CONF_URL_PATH) == dashboard_url:
            return

    try:
        item = await dashboards_collection.async_create_item(
            {
                CONF_ICON: _DASHBOARD_ICON,
                CONF_TITLE: dashboard_title,
                CONF_URL_PATH: dashboard_url,
                CONF_REQUIRE_ADMIN: _DASHBOARD_REQUIRE_ADMIN,
                CONF_SHOW_IN_SIDEBAR: _DASHBOARD_SHOW_IN_SIDEBAR,
            }
        )
    except (HomeAssistantError, ValueError):
        return

    lovelace_config = LovelaceStorage(hass, item)
    await lovelace_config.async_save(dashboard_config)
    hass.data[LOVELACE_DATA].dashboards[dashboard_url] = lovelace_config

    frontend.async_register_built_in_panel(
        hass,
        "lovelace",
        frontend_url_path=dashboard_url,
        require_admin=_DASHBOARD_REQUIRE_ADMIN,
        show_in_sidebar=_DASHBOARD_SHOW_IN_SIDEBAR,
        sidebar_title=dashboard_title,
        sidebar_icon=_DASHBOARD_ICON,
        config={"mode": "storage"},
        update=False,
    )


def _default_dashboard_config(connection_name: str = DEFAULT_CONNECTION_NAME) -> dict:
    """Return versioned Lovelace dashboard config for an Alby Hub instance."""
    # Entity IDs are derived from: {domain}.{device_slug}_{entity_key}
    # where device_slug = slugify(connection_name) and entity_key matches sensor/entity key
    p = _entity_slug(connection_name)

    return {
        "title": connection_name,
        "_version": DASHBOARD_VERSION,
        "views": [
            # ── Overview ──────────────────────────────────────────────────────
            {
                "title": "Overview",
                "path": "overview",
                "icon": "mdi:view-dashboard",
                "badges": [
                    f"binary_sensor.{p}_node_online",
                ],
                "cards": [
                    # ── Status & balance summary ─────────────────────────────
                    {
                        "type": "markdown",
                        "content": (
                            f"# ⚡ {connection_name}\n\n"
                            f"{{% set lightning = states('sensor.{p}_lightning_balance') | int(0) %}}\n"
                            f"{{% set onchain = states('sensor.{p}_on_chain_balance') | int(0) %}}\n"
                            f"{{% set price = states('sensor.{p}_bitcoin_price') | float(0) %}}\n"
                            f"{{% set currency = state_attr('sensor.{p}_bitcoin_price', 'unit_of_measurement') | default('') %}}\n"
                            f"{{% set connected = is_state('binary_sensor.{p}_node_online', 'on') %}}\n"
                            "{% if connected %}✅ **Connected**{% else %}🔴 **Offline**{% endif %}\n\n"
                            "| | ⚡ Lightning | ₿ On-chain |\n"
                            "|---|---|---|\n"
                            "| **sat** | {{ lightning }} | {{ onchain }} |\n"
                            "| **BTC** | {{ (lightning / 100000000) | round(8) }} | {{ (onchain / 100000000) | round(8) }} |\n"
                            "{% if price > 0 %}"
                            "| **≈ {{ currency }}** | {{ ((lightning / 100000000) * price) | round(2) }} | {{ ((onchain / 100000000) * price) | round(2) }} |\n"
                            "{% endif %}"
                        ),
                    },
                    # ── Balance entities side by side ────────────────────────
                    {
                        "type": "horizontal-stack",
                        "cards": [
                            {
                                "type": "entity",
                                "entity": f"sensor.{p}_lightning_balance",
                                "name": "Lightning Balance",
                                "icon": "mdi:lightning-bolt",
                            },
                            {
                                "type": "entity",
                                "entity": f"sensor.{p}_on_chain_balance",
                                "name": "On-chain Balance",
                                "icon": "mdi:bitcoin",
                            },
                        ],
                    },
                    # ── Bitcoin price & block height side by side ────────────
                    {
                        "type": "horizontal-stack",
                        "cards": [
                            {
                                "type": "entity",
                                "entity": f"sensor.{p}_bitcoin_price",
                                "name": "Bitcoin Price",
                                "icon": "mdi:currency-btc",
                            },
                            {
                                "type": "entity",
                                "entity": f"sensor.{p}_bitcoin_block_height",
                                "name": "Block Height",
                                "icon": "mdi:cube-outline",
                            },
                        ],
                    },
                    # ── Connection info ──────────────────────────────────────
                    {
                        "type": "entities",
                        "title": "Connection",
                        "show_header_toggle": False,
                        "entities": [
                            f"binary_sensor.{p}_node_online",
                            f"sensor.{p}_nwc_relay",
                            f"sensor.{p}_hub_version",
                            f"sensor.{p}_lightning_address",
                        ],
                    },
                ],
            },
            # ── Receive ───────────────────────────────────────────────────────
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
                                "entity": f"number.{p}_invoice_amount",
                                "name": "Amount",
                            },
                            {
                                "entity": f"select.{p}_invoice_amount_unit",
                                "name": "Unit (SAT / BTC / Fiat)",
                            },
                            {
                                "entity": f"button.{p}_create_invoice",
                                "name": "Create Invoice",
                            },
                        ],
                    },
                    # ── Show generated BOLT11 invoice + QR ───────────────────
                    {
                        "type": "markdown",
                        "title": "BOLT11 Invoice & QR Code",
                        "content": (
                            f"{{% set inv = states('text.{p}_last_invoice') %}}\n"
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
                    # ── Lightning address & QR ────────────────────────────────
                    {
                        "type": "entities",
                        "title": "Lightning Address",
                        "show_header_toggle": False,
                        "entities": [f"sensor.{p}_lightning_address"],
                    },
                    {
                        "type": "markdown",
                        "title": "Lightning Address QR (receive without fixed amount)",
                        "content": (
                            f"{{% set addr = states('sensor.{p}_lightning_address') %}}\n"
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
                        "type": "horizontal-stack",
                        "cards": [
                            {
                                "type": "entity",
                                "entity": f"sensor.{p}_lightning_balance",
                                "name": "Lightning Balance",
                            },
                            {
                                "type": "entity",
                                "entity": f"sensor.{p}_on_chain_balance",
                                "name": "On-chain Balance",
                            },
                        ],
                    },
                ],
            },
            # ── Send ──────────────────────────────────────────────────────────
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
                                "entity": f"text.{p}_invoice_input",
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
                        "type": "horizontal-stack",
                        "cards": [
                            {
                                "type": "entity",
                                "entity": f"sensor.{p}_lightning_balance",
                                "name": "Lightning Balance",
                            },
                            {
                                "type": "entity",
                                "entity": f"sensor.{p}_on_chain_balance",
                                "name": "On-chain Balance",
                            },
                        ],
                    },
                ],
            },
            # ── NWC Budget ────────────────────────────────────────────────────
            {
                "title": "NWC Budget",
                "path": "budget",
                "icon": "mdi:cash-lock",
                "cards": [
                    # ── Dynamic budget summary ───────────────────────────────
                    {
                        "type": "markdown",
                        "title": "Budget Usage",
                        "content": (
                            f"{{% set total = states('sensor.{p}_nwc_budget_total') | int(0) %}}\n"
                            f"{{% set used = states('sensor.{p}_nwc_budget_used') | int(0) %}}\n"
                            f"{{% set remaining = states('sensor.{p}_nwc_budget_remaining') | int(0) %}}\n"
                            f"{{% set renewal = states('sensor.{p}_nwc_budget_renewal_period') %}}\n"
                            "{% if total > 0 %}\n"
                            "{% set pct_used = (used / total * 100) | round(1) %}\n"
                            "{% set pct_remaining = (remaining / total * 100) | round(1) %}\n"
                            "{% if pct_used >= 90 %}🔴{% elif pct_used >= 70 %}🟠{% elif pct_used >= 50 %}🟡{% else %}🟢{% endif %} "
                            "**{{ pct_used }}% used** ({{ used }} / {{ total }} sat)\n\n"
                            "Remaining: **{{ remaining }} sat** ({{ pct_remaining }}%)  \n"
                            "Renewal: **{{ renewal }}**\n"
                            "{% else %}\n"
                            "*No budget limit configured, or hub does not support get_budget.*\n"
                            "{% endif %}"
                        ),
                    },
                    # ── Budget entities ──────────────────────────────────────
                    {
                        "type": "entities",
                        "title": "NWC Spending Limits",
                        "show_header_toggle": False,
                        "entities": [
                            f"sensor.{p}_nwc_budget_total",
                            f"sensor.{p}_nwc_budget_used",
                            f"sensor.{p}_nwc_budget_remaining",
                            f"sensor.{p}_nwc_budget_renewal_period",
                        ],
                    },
                    {
                        "type": "markdown",
                        "title": "About NWC Budget",
                        "content": (
                            "These sensors show the spending limits configured for this NWC "
                            "connection.  \n\n"
                            "- **Total budget** – maximum amount this connection may spend per renewal period\n"
                            "- **Used budget** – amount already spent in the current period\n"
                            "- **Remaining budget** – amount still available to spend\n"
                            "- **Renewal period** – how often the budget resets (daily / weekly / monthly / …)\n\n"
                            "*Sensors show 'unavailable' if the NWC connection has no budget limit "
                            "or if your hub does not support the get_budget method.*"
                        ),
                    },
                ],
            },
            # ── Network ───────────────────────────────────────────────────────
            {
                "title": "Network",
                "path": "network",
                "icon": "mdi:bitcoin",
                "cards": [
                    # ── Market & network entities ────────────────────────────
                    {
                        "type": "entities",
                        "title": "Bitcoin Market & Network",
                        "show_header_toggle": False,
                        "entities": [
                            f"sensor.{p}_bitcoin_price",
                            f"sensor.{p}_bitcoin_block_height",
                            f"sensor.{p}_bitcoin_hashrate",
                            f"sensor.{p}_blocks_until_halving",
                            f"sensor.{p}_next_halving_estimate",
                        ],
                    },
                    # ── Bitcoin price history graph ───────────────────────────
                    {
                        "type": "history-graph",
                        "title": "Bitcoin Price (last 7 days)",
                        "hours_to_show": 168,
                        "refresh_interval": 0,
                        "entities": [
                            {
                                "entity": f"sensor.{p}_bitcoin_price",
                                "name": "BTC Price",
                            }
                        ],
                    },
                    # ── Halving countdown markdown ───────────────────────────
                    {
                        "type": "markdown",
                        "title": "Next Halving",
                        "content": (
                            f"{{% set blocks = states('sensor.{p}_blocks_until_halving') | int(0) %}}\n"
                            f"{{% set eta = states('sensor.{p}_next_halving_estimate') %}}\n"
                            "{% if blocks > 0 %}\n"
                            "⛏️ **{{ blocks | int }} blocks** remaining until the next halving.\n\n"
                            "📅 Estimated date: **{{ as_timestamp(eta) | timestamp_local }}**\n"
                            "{% else %}\n"
                            "*Halving data not available.*\n"
                            "{% endif %}"
                        ),
                    },
                ],
            },
        ],
    }
