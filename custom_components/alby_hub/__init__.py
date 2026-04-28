"""Alby Hub integration."""

from __future__ import annotations

import logging
from dataclasses import replace
from pathlib import Path

from homeassistant.components.http import StaticPathConfig
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlbyHubApiClient
from .const import (
    CONF_CONNECTION_NAME,
    CONF_HUB_URL,
    CONF_LIGHTNING_ADDRESS,
    CONF_MODE,
    CONF_NETWORK_API_BASE,
    CONF_NETWORK_PROVIDER,
    CONF_NOSTR_ALLOWED_NPUBS,
    CONF_NOSTR_BOT_NSEC,
    CONF_NOSTR_ENABLED,
    CONF_NOSTR_ENCRYPTION_MODE,
    CONF_NOSTR_RELAY,
    CONF_NOSTR_RELAYS,
    CONF_NOSTR_WEBHOOK_SECRET,
    CONF_NWC_URI,
    CONF_PRICE_CURRENCY,
    CONF_PRICE_PROVIDER,
    CONF_RELAY_OVERRIDE,
    DEFAULT_CONNECTION_NAME,
    DEFAULT_NETWORK_PROVIDER,
    DEFAULT_NOSTR_ENCRYPTION_MODE,
    DEFAULT_PRICE_CURRENCY,
    DEFAULT_PRICE_PROVIDER,
    DOMAIN,
    MODE_EXPERT,
)
from .coordinator import AlbyHubDataUpdateCoordinator
from .helpers import AlbyHubRuntime
from .nostr_bot import AlbyHubNostrWebhookView, AlbyHubNostrBotManager
from .nostr_relay_listener import NostrRelayListener
from .nwc import parse_nwc_connection_uri
from .address_book import async_setup_address_book
from .recurring_payments import async_setup_scheduler, async_unload_scheduler
from .services import async_setup_services, async_unload_services
# Preload all platform modules into sys.modules while still in the executor
# (package load time).  This guarantees that when HA's _load_platform calls
# importlib.import_module from within the event loop, the modules are already
# cached and the call returns immediately -- avoiding both the blocking-import
# warning AND the RuntimeError that HA raises when the import of a not-yet-
# cached HA core module (e.g. homeassistant.components.text) is triggered
# from the event loop as a side-effect.
from . import binary_sensor, button, number, select, sensor, text  # noqa: F401
from . import notify, recurring_payments  # noqa: F401

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [
    Platform.SENSOR,
    Platform.BINARY_SENSOR,
    Platform.TEXT,
    Platform.NUMBER,
    Platform.SELECT,
    Platform.BUTTON,
    Platform.NOTIFY,
]

# Frontend panel configuration
_CARD_VERSION = "7"
_PANEL_FILENAME = "alby-hub-card.js"
_PANEL_URL_PATH = "alby-hub-panel"
_PANEL_ELEMENT_NAME = "alby-hub-panel"
_PANEL_ICON = "mdi:lightning-bolt"


async def async_setup(hass: HomeAssistant, config: dict) -> bool:
    """Set up the Alby Hub integration."""
    await _async_register_frontend(hass)
    if not hass.data.get(f"{DOMAIN}_nostr_webhook_view_registered"):
        hass.http.register_view(AlbyHubNostrWebhookView(hass))
        hass.data[f"{DOMAIN}_nostr_webhook_view_registered"] = True
    return True


async def _async_register_frontend(hass: HomeAssistant) -> None:
    """Register the Alby Hub custom panel and static JS assets.

    Serves the ``www/`` subfolder at ``/{DOMAIN}_local/`` and registers a
    ``panel_custom`` sidebar entry so users reach the integration-specific
    dashboard without any manual Lovelace configuration.

    This is idempotent – calling it more than once (e.g. during a reload) is
    safe because HA silently ignores duplicate static-path registrations and
    we guard the panel registration with a flag.
    """
    if hass.data.get(f"{DOMAIN}_frontend_registered"):
        return

    www_dir = Path(__file__).parent / "www"
    card_url = f"/{DOMAIN}_local/{_PANEL_FILENAME}?v={_CARD_VERSION}"

    try:
        await hass.http.async_register_static_paths([
            StaticPathConfig(
                url_path=f"/{DOMAIN}_local",
                path=str(www_dir),
                cache_headers=False,
            )
        ])
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Static path already registered or failed: %s", err)

    try:
        from homeassistant.components.panel_custom import async_register_panel  # noqa: PLC0415

        await async_register_panel(
            hass,
            frontend_url_path=_PANEL_URL_PATH,
            webcomponent_name=_PANEL_ELEMENT_NAME,
            sidebar_title="Alby Hub",
            sidebar_icon=_PANEL_ICON,
            module_url=card_url,
            embed_iframe=False,
            trust_external=False,
            require_admin=False,
        )
        _LOGGER.info("Alby Hub panel registered at /%s (module: %s)", _PANEL_URL_PATH, card_url)
    except Exception as err:  # noqa: BLE001
        _LOGGER.debug("Panel registration skipped (already registered or failed): %s", err)

    hass.data[f"{DOMAIN}_frontend_registered"] = True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Alby Hub from a config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data.setdefault(f"{DOMAIN}_nostr_managers", {})

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
        manual_lightning_address=merged.get(CONF_LIGHTNING_ADDRESS) or None,
    )
    await coordinator.async_config_entry_first_refresh()

    runtime = AlbyHubRuntime(
        coordinator=coordinator,
        api_client=api_client,
        nwc_info=nwc_info,
        session=session,
    )
    hass.data[DOMAIN][entry.entry_id] = runtime

    if merged.get(CONF_NOSTR_ENABLED):
        # Resolve relay list — support both new list field and legacy single-string field
        relay_urls_raw = merged.get(CONF_NOSTR_RELAYS)
        if isinstance(relay_urls_raw, list):
            relay_urls = [u.strip() for u in relay_urls_raw if u and u.strip()]
        else:
            single = str(merged.get(CONF_NOSTR_RELAY, "")).strip()
            relay_urls = [single] if single else []
        encryption_mode = str(
            merged.get(CONF_NOSTR_ENCRYPTION_MODE, DEFAULT_NOSTR_ENCRYPTION_MODE)
        )
        manager = AlbyHubNostrBotManager(
            hass=hass,
            entry_id=entry.entry_id,
            relay_urls=relay_urls,
            bot_nsec=str(merged.get(CONF_NOSTR_BOT_NSEC, "")),
            allowed_npubs=str(merged.get(CONF_NOSTR_ALLOWED_NPUBS, "")),
            webhook_secret=str(merged.get(CONF_NOSTR_WEBHOOK_SECRET, "")),
            encryption_mode=encryption_mode,
        )
        runtime.nostr_bot_manager = manager
        hass.data[f"{DOMAIN}_nostr_managers"][entry.entry_id] = manager

        # Start relay listener when the bot has a valid key and relay list
        if manager.bot_nsec and relay_urls:
            from .nostr_client import parse_key_to_hex, _derive_pubkey_x_hex  # noqa: PLC0415
            try:
                bot_priv_hex = parse_key_to_hex(manager.bot_nsec, "nsec")
                bot_pub_hex = _derive_pubkey_x_hex(bot_priv_hex)
                listener = NostrRelayListener(
                    session=session,
                    manager=manager,
                    relay_urls=relay_urls,
                    bot_priv_hex=bot_priv_hex,
                    bot_pub_hex=bot_pub_hex,
                )
                await listener.async_start()
                runtime.nostr_relay_listener = listener
            except Exception as err:  # noqa: BLE001
                _LOGGER.warning("Could not start Nostr relay listener: %s", err)

    await async_setup_services(hass)
    await async_setup_scheduler(hass)
    await async_setup_address_book(hass)

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Reload the entry whenever options are saved via the gear icon
    entry.async_on_unload(entry.add_update_listener(_async_options_update_listener))

    return True


async def _async_options_update_listener(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload the config entry when options are updated."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    # Stop Nostr relay listener before unloading platforms
    runtime: AlbyHubRuntime | None = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if runtime is not None and runtime.nostr_relay_listener is not None:
        await runtime.nostr_relay_listener.async_stop()
        runtime.nostr_relay_listener = None

    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
        hass.data.get(f"{DOMAIN}_nostr_managers", {}).pop(entry.entry_id, None)

    if not hass.data[DOMAIN]:
        await async_unload_services(hass)
        await async_unload_scheduler(hass)

    return unload_ok
