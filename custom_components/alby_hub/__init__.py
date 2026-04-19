"""Alby Hub integration."""

from __future__ import annotations

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
    CONF_NETWORK_PROVIDER,
    CONF_NWC_URI,
    CONF_PRICE_CURRENCY,
    CONF_PRICE_PROVIDER,
    CONF_RELAY_OVERRIDE,
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

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.BINARY_SENSOR]


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up integration from YAML (unused)."""
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alby Hub from a config entry."""
    hass.data.setdefault(DOMAIN, {})

    nwc_info = parse_nwc_connection_uri(entry.data[CONF_NWC_URI])
    relay_override = entry.data.get(CONF_RELAY_OVERRIDE)
    if relay_override:
        nwc_info = replace(nwc_info, relay=relay_override)

    mode = entry.data[CONF_MODE]
    session = async_get_clientsession(hass)
    api_client = None
    if mode == MODE_EXPERT:
        hub_url = entry.data.get(CONF_HUB_URL)
        if hub_url:
            api_client = AlbyHubApiClient(session, hub_url)

    coordinator = AlbyHubDataUpdateCoordinator(
        hass,
        mode=mode,
        nwc_info=nwc_info,
        api_client=api_client,
        session=session,
        price_provider=entry.data.get(CONF_PRICE_PROVIDER, DEFAULT_PRICE_PROVIDER),
        price_currency=entry.data.get(CONF_PRICE_CURRENCY, DEFAULT_PRICE_CURRENCY),
        network_provider=entry.data.get(CONF_NETWORK_PROVIDER, DEFAULT_NETWORK_PROVIDER),
        network_api_base=entry.data.get(CONF_HUB_URL),
    )
    await coordinator.async_config_entry_first_refresh()

    hass.data[DOMAIN][entry.entry_id] = AlbyHubRuntime(
        coordinator=coordinator,
        api_client=api_client,
        nwc_info=nwc_info,
    )

    await async_setup_services(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    await _async_ensure_dashboard(hass)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)

    if not hass.data[DOMAIN]:
        await async_unload_services(hass)

    return unload_ok


async def _async_ensure_dashboard(hass: HomeAssistant) -> None:
    """Create an Alby Hub dashboard with starter cards when missing."""
    if LOVELACE_DATA not in hass.data:
        return

    dashboard_url = "alby-hub"
    if dashboard_url in hass.data[LOVELACE_DATA].dashboards:
        return

    dashboards_collection = DashboardsCollection(hass)
    await dashboards_collection.async_load()
    for item in dashboards_collection.async_items():
        if item.get(CONF_URL_PATH) == dashboard_url:
            return

    try:
        item = await dashboards_collection.async_create_item(
            {
                CONF_ICON: "mdi:lightning-bolt",
                CONF_TITLE: "Alby Hub",
                CONF_URL_PATH: dashboard_url,
                CONF_REQUIRE_ADMIN: False,
                CONF_SHOW_IN_SIDEBAR: True,
            }
        )
    except (HomeAssistantError, ValueError):
        return

    lovelace_config = LovelaceStorage(hass, item)
    await lovelace_config.async_save(_default_dashboard_config())
    hass.data[LOVELACE_DATA].dashboards[dashboard_url] = lovelace_config

    frontend.async_register_built_in_panel(
        hass,
        "lovelace",
        frontend_url_path=dashboard_url,
        require_admin=False,
        show_in_sidebar=True,
        sidebar_title="Alby Hub",
        sidebar_icon="mdi:lightning-bolt",
        config={"mode": "storage"},
        update=False,
    )


def _default_dashboard_config() -> dict:
    """Return initial Lovelace dashboard cards for Alby Hub."""
    return {
        "title": "Alby Hub",
        "views": [
            {
                "title": "Lightning",
                "path": "lightning",
                "icon": "mdi:lightning-bolt",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Empfangen",
                        "show_header_toggle": False,
                        "entities": [
                            "sensor.alby_hub_lightning_address",
                            "sensor.alby_hub_relay",
                        ],
                    },
                    {
                        "type": "markdown",
                        "title": "Rechnung / BOLT12 / Lightning-Adresse",
                        "content": "Nutze deine Lightning-Adresse oder erstelle Rechnungen über den Service `alby_hub.create_invoice`.",
                    },
                    {
                        "type": "markdown",
                        "title": "Senden",
                        "content": "Scanne den QR-Code in der Home Assistant Companion App/Kamera oder füge die Rechnung per Copy & Paste ein und sende dann über `alby_hub.send_payment`.",
                    },
                    {
                        "type": "entities",
                        "title": "Bitcoin Markt & Netzwerk",
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
            }
        ],
    }
