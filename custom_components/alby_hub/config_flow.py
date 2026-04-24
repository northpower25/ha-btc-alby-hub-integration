"""Config flow for Alby Hub integration."""

from __future__ import annotations

import secrets
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlbyHubApiClient
from .const import (
    COMMON_FIAT_CURRENCIES,
    CONF_ALLOW_CONTINUE_WITH_WARNING,
    CONF_CONNECTION_NAME,
    CONF_HUB_URL,
    CONF_LIGHTNING_ADDRESS,
    CONF_MODE,
    CONF_NETWORK_API_BASE,
    CONF_NETWORK_PROVIDER,
    CONF_NOSTR_ALLOWED_NPUBS,
    CONF_NOSTR_BOT_NPUB,
    CONF_NOSTR_BOT_NSEC,
    CONF_NOSTR_ENABLED,
    CONF_NOSTR_RELAY,
    CONF_NOSTR_RELAYS,
    CONF_NOSTR_WEBHOOK_SECRET,
    CONF_NWC_URI,
    CONF_PREFER_LOCAL_RELAY,
    CONF_PRICE_CURRENCY,
    CONF_PRICE_PROVIDER,
    CONF_RELAY_OVERRIDE,
    CONF_SETUP_WARNINGS,
    DEFAULT_CONNECTION_NAME,
    DEFAULT_NETWORK_PROVIDER,
    DEFAULT_NOSTR_RELAY,
    DEFAULT_NOSTR_RELAYS,
    DEFAULT_HUB_URL,
    DEFAULT_PRICE_CURRENCY,
    DEFAULT_PRICE_PROVIDER,
    DOMAIN,
    MODE_CLOUD,
    MODE_EXPERT,
    NETWORK_PROVIDER_CUSTOM_NODE,
    NETWORK_PROVIDER_MEMPOOL,
    PRICE_PROVIDER_BINANCE,
    PRICE_PROVIDER_BITCOIN_DE,
    PRICE_PROVIDER_BITQUERY,
    PRICE_PROVIDER_BLOCKCHAIN,
    PRICE_PROVIDER_COINDESK,
    PRICE_PROVIDER_COINGECKO,
    PRICE_PROVIDER_COINBASE,
    PRICE_PROVIDER_MEMPOOL,
    RELAY_PROXY_PORT,
)
from .nwc import NwcConnectionInfo, ScopeValidationResult, parse_nwc_connection_uri, validate_scopes
from .nostr_client import npub_from_nsec, nsec_from_hex


def _currency_selector() -> selector.SelectSelector:
    """Return a searchable dropdown for fiat currencies with custom-value support."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=c, label=c)
                for c in COMMON_FIAT_CURRENCIES
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
            custom_value=True,
        )
    )


def _price_provider_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=PRICE_PROVIDER_COINGECKO, label="CoinGecko"),
                selector.SelectOptionDict(value=PRICE_PROVIDER_COINDESK, label="CoinDesk"),
                selector.SelectOptionDict(value=PRICE_PROVIDER_COINBASE, label="Coinbase"),
                selector.SelectOptionDict(value=PRICE_PROVIDER_BINANCE, label="Binance"),
                selector.SelectOptionDict(value=PRICE_PROVIDER_BLOCKCHAIN, label="Blockchain.com"),
                selector.SelectOptionDict(value=PRICE_PROVIDER_MEMPOOL, label="Mempool"),
                selector.SelectOptionDict(
                    value=PRICE_PROVIDER_BITCOIN_DE, label="Bitcoin.de (not yet implemented)"
                ),
                selector.SelectOptionDict(
                    value=PRICE_PROVIDER_BITQUERY, label="Bitquery (not yet implemented)"
                ),
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _network_provider_selector() -> selector.SelectSelector:
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=NETWORK_PROVIDER_MEMPOOL, label="Mempool"),
                selector.SelectOptionDict(value=NETWORK_PROVIDER_CUSTOM_NODE, label="Custom Node"),
            ],
            mode=selector.SelectSelectorMode.DROPDOWN,
        )
    )


def _nostr_relay_selector() -> selector.SelectSelector:
    """Return a multi-select selector for Nostr relays with predefined suggestions and custom-value support."""
    return selector.SelectSelector(
        selector.SelectSelectorConfig(
            options=[
                selector.SelectOptionDict(value=r, label=r)
                for r in DEFAULT_NOSTR_RELAYS
            ],
            multiple=True,
            custom_value=True,
            mode=selector.SelectSelectorMode.LIST,
        )
    )


class AlbyHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alby Hub."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize flow state."""
        super().__init__()
        self._pending_data: dict = {}
        self._pending_title: str = ""
        self._generated_nsec: str = ""
        self._generated_npub: str = ""

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "AlbyHubOptionsFlowHandler":
        """Return the options flow handler (gear icon)."""
        return AlbyHubOptionsFlowHandler()

    async def async_step_user(self, user_input=None):
        """Handle the initial step."""
        if user_input is not None:
            mode = user_input[CONF_MODE]
            if mode == MODE_CLOUD:
                return await self.async_step_cloud()
            return await self.async_step_expert()

        schema = vol.Schema(
            {
                vol.Required(CONF_MODE, default=MODE_CLOUD): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[
                            selector.SelectOptionDict(value=MODE_CLOUD, label="Cloud"),
                            selector.SelectOptionDict(value=MODE_EXPERT, label="Expert"),
                        ],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                )
            }
        )
        return self.async_show_form(step_id="user", data_schema=schema)

    async def async_step_cloud(self, user_input=None):
        """Cloud mode setup via NWC."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            try:
                nwc_info = parse_nwc_connection_uri(user_input[CONF_NWC_URI])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                scope_result = validate_scopes(nwc_info)
                warnings = _warnings_from_scope_result(scope_result)
                allow_continue = user_input[CONF_ALLOW_CONTINUE_WITH_WARNING]

                if warnings and not allow_continue:
                    errors["base"] = "warning_ack_required"
                    placeholders["warnings"] = "\n".join(warnings)
                else:
                    nostr_data = _normalize_nostr_config(user_input, errors)
                    if nostr_data is None:
                        return self.async_show_form(
                            step_id="cloud",
                            data_schema=_cloud_schema(user_input),
                            errors=errors,
                            description_placeholders=placeholders,
                        )
                    await self.async_set_unique_id(f"{nwc_info.wallet_pubkey}:{nwc_info.relay}")
                    self._abort_if_unique_id_configured()
                    connection_name = (
                        user_input.get(CONF_CONNECTION_NAME, "").strip()
                        or DEFAULT_CONNECTION_NAME
                    )
                    entry_data = {
                        CONF_MODE: MODE_CLOUD,
                        CONF_NWC_URI: nwc_info.raw_uri,
                        CONF_CONNECTION_NAME: connection_name,
                        CONF_LIGHTNING_ADDRESS: _resolve_lightning_address(user_input, nwc_info),
                        CONF_PRICE_PROVIDER: user_input[CONF_PRICE_PROVIDER],
                        CONF_PRICE_CURRENCY: user_input[CONF_PRICE_CURRENCY],
                        CONF_NETWORK_PROVIDER: user_input[CONF_NETWORK_PROVIDER],
                        CONF_NETWORK_API_BASE: user_input.get(CONF_NETWORK_API_BASE),
                        CONF_SETUP_WARNINGS: warnings,
                        **nostr_data,
                    }
                    nostr_enabled = bool(user_input.get(CONF_NOSTR_ENABLED, False))
                    bot_nsec_input = (user_input.get(CONF_NOSTR_BOT_NSEC, "") or "").strip()
                    if nostr_enabled and not bot_nsec_input:
                        generated_nsec, generated_npub = _generate_nostr_bot_keys()
                        entry_data[CONF_NOSTR_BOT_NSEC] = generated_nsec
                        entry_data[CONF_NOSTR_BOT_NPUB] = generated_npub
                        self._pending_data = entry_data
                        self._pending_title = connection_name
                        self._generated_nsec = generated_nsec
                        self._generated_npub = generated_npub
                        return await self.async_step_nostr_keygen()
                    return self.async_create_entry(title=connection_name, data=entry_data)

        return self.async_show_form(
            step_id="cloud",
            data_schema=_cloud_schema(user_input),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_expert(self, user_input=None):
        """Expert mode setup with optional local API."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            warnings: list[str] = []
            hub_url = user_input.get(CONF_HUB_URL, "").strip() or DEFAULT_HUB_URL

            try:
                nwc_info = parse_nwc_connection_uri(user_input[CONF_NWC_URI])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                scope_result = validate_scopes(nwc_info)
                warnings.extend(_warnings_from_scope_result(scope_result))

                session = async_get_clientsession(self.hass)
                api_client = AlbyHubApiClient(session, hub_url)
                if not await api_client.health_check():
                    warnings.append("Local API health check failed")

                relay_override = None
                if user_input[CONF_PREFER_LOCAL_RELAY]:
                    relay_override = _build_local_relay(hub_url)

                allow_continue = user_input[CONF_ALLOW_CONTINUE_WITH_WARNING]
                if warnings and not allow_continue:
                    errors["base"] = "warning_ack_required"
                    placeholders["warnings"] = "\n".join(warnings)
                else:
                    nostr_data = _normalize_nostr_config(user_input, errors)
                    if nostr_data is None:
                        return self.async_show_form(
                            step_id="expert",
                            data_schema=_expert_schema(user_input),
                            errors=errors,
                            description_placeholders=placeholders,
                        )
                    await self.async_set_unique_id(f"{nwc_info.wallet_pubkey}:{hub_url}")
                    self._abort_if_unique_id_configured()
                    connection_name = (
                        user_input.get(CONF_CONNECTION_NAME, "").strip()
                        or DEFAULT_CONNECTION_NAME
                    )
                    entry_data = {
                        CONF_MODE: MODE_EXPERT,
                        CONF_NWC_URI: nwc_info.raw_uri,
                        CONF_CONNECTION_NAME: connection_name,
                        CONF_HUB_URL: hub_url,
                        CONF_LIGHTNING_ADDRESS: _resolve_lightning_address(user_input, nwc_info),
                        CONF_PRICE_PROVIDER: user_input[CONF_PRICE_PROVIDER],
                        CONF_PRICE_CURRENCY: user_input[CONF_PRICE_CURRENCY],
                        CONF_NETWORK_PROVIDER: user_input[CONF_NETWORK_PROVIDER],
                        CONF_NETWORK_API_BASE: user_input.get(CONF_NETWORK_API_BASE),
                        CONF_SETUP_WARNINGS: warnings,
                        CONF_PREFER_LOCAL_RELAY: user_input[CONF_PREFER_LOCAL_RELAY],
                        **nostr_data,
                    }
                    if relay_override:
                        entry_data[CONF_RELAY_OVERRIDE] = relay_override
                    nostr_enabled = bool(user_input.get(CONF_NOSTR_ENABLED, False))
                    bot_nsec_input = (user_input.get(CONF_NOSTR_BOT_NSEC, "") or "").strip()
                    if nostr_enabled and not bot_nsec_input:
                        generated_nsec, generated_npub = _generate_nostr_bot_keys()
                        entry_data[CONF_NOSTR_BOT_NSEC] = generated_nsec
                        entry_data[CONF_NOSTR_BOT_NPUB] = generated_npub
                        self._pending_data = entry_data
                        self._pending_title = connection_name
                        self._generated_nsec = generated_nsec
                        self._generated_npub = generated_npub
                        return await self.async_step_nostr_keygen()
                    return self.async_create_entry(title=connection_name, data=entry_data)

        return self.async_show_form(
            step_id="expert",
            data_schema=_expert_schema(user_input),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_nostr_keygen(self, user_input=None):
        """Display generated Nostr bot keys and require the user to confirm they are saved."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("keys_saved"):
                return self.async_create_entry(
                    title=self._pending_title,
                    data=self._pending_data,
                )
            errors["keys_saved"] = "keys_not_saved"

        return self.async_show_form(
            step_id="nostr_keygen",
            data_schema=vol.Schema({vol.Required("keys_saved", default=False): bool}),
            errors=errors,
            description_placeholders={
                "npub": self._generated_npub,
                "nsec": self._generated_nsec,
            },
        )


class AlbyHubOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Alby Hub (gear icon reconfiguration)."""

    def __init__(self) -> None:
        """Initialize flow state."""
        super().__init__()
        self._pending_data: dict = {}
        self._generated_nsec: str = ""
        self._generated_npub: str = ""

    async def async_step_init(self, user_input=None):
        """Route to the correct options step based on current mode."""
        mode = self.config_entry.data.get(CONF_MODE, MODE_CLOUD)
        if mode == MODE_CLOUD:
            return await self.async_step_cloud(user_input)
        return await self.async_step_expert(user_input)

    async def async_step_cloud(self, user_input=None):
        """Cloud mode options: update connection and price/network settings."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            try:
                nwc_info = parse_nwc_connection_uri(user_input[CONF_NWC_URI])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                scope_result = validate_scopes(nwc_info)
                warnings = _warnings_from_scope_result(scope_result)
                allow_continue = user_input[CONF_ALLOW_CONTINUE_WITH_WARNING]

                if warnings and not allow_continue:
                    errors["base"] = "warning_ack_required"
                    placeholders["warnings"] = "\n".join(warnings)
                else:
                    nostr_data = _normalize_nostr_config(user_input, errors)
                    if nostr_data is None:
                        return self.async_show_form(
                            step_id="cloud",
                            data_schema=_cloud_schema(_merged_entry_data(self.config_entry)),
                            errors=errors,
                            description_placeholders=placeholders,
                        )
                    new_data = {
                        CONF_NWC_URI: nwc_info.raw_uri,
                        CONF_CONNECTION_NAME: (
                            user_input.get(CONF_CONNECTION_NAME, "").strip()
                            or DEFAULT_CONNECTION_NAME
                        ),
                        CONF_LIGHTNING_ADDRESS: _resolve_lightning_address(user_input, nwc_info),
                        CONF_PRICE_PROVIDER: user_input[CONF_PRICE_PROVIDER],
                        CONF_PRICE_CURRENCY: user_input[CONF_PRICE_CURRENCY],
                        CONF_NETWORK_PROVIDER: user_input[CONF_NETWORK_PROVIDER],
                        CONF_NETWORK_API_BASE: user_input.get(CONF_NETWORK_API_BASE),
                        **nostr_data,
                    }
                    nostr_enabled = bool(user_input.get(CONF_NOSTR_ENABLED, False))
                    bot_nsec_input = (user_input.get(CONF_NOSTR_BOT_NSEC, "") or "").strip()
                    if nostr_enabled and not bot_nsec_input:
                        generated_nsec, generated_npub = _generate_nostr_bot_keys()
                        new_data[CONF_NOSTR_BOT_NSEC] = generated_nsec
                        new_data[CONF_NOSTR_BOT_NPUB] = generated_npub
                        self._pending_data = new_data
                        self._generated_nsec = generated_nsec
                        self._generated_npub = generated_npub
                        return await self.async_step_nostr_keygen()
                    return self.async_create_entry(title="", data=new_data)

        return self.async_show_form(
            step_id="cloud",
            data_schema=_cloud_schema(_merged_entry_data(self.config_entry)),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_expert(self, user_input=None):
        """Expert mode options: update all expert settings."""
        errors: dict[str, str] = {}
        placeholders: dict[str, str] = {}

        if user_input is not None:
            warnings: list[str] = []
            hub_url = user_input.get(CONF_HUB_URL, "").strip() or DEFAULT_HUB_URL

            try:
                nwc_info = parse_nwc_connection_uri(user_input[CONF_NWC_URI])
            except ValueError as err:
                errors["base"] = str(err)
            else:
                scope_result = validate_scopes(nwc_info)
                warnings.extend(_warnings_from_scope_result(scope_result))

                relay_override = None
                if user_input[CONF_PREFER_LOCAL_RELAY]:
                    relay_override = _build_local_relay(hub_url)

                allow_continue = user_input[CONF_ALLOW_CONTINUE_WITH_WARNING]
                if warnings and not allow_continue:
                    errors["base"] = "warning_ack_required"
                    placeholders["warnings"] = "\n".join(warnings)
                else:
                    nostr_data = _normalize_nostr_config(user_input, errors)
                    if nostr_data is None:
                        return self.async_show_form(
                            step_id="expert",
                            data_schema=_expert_schema(_merged_entry_data(self.config_entry)),
                            errors=errors,
                            description_placeholders=placeholders,
                        )
                    new_data: dict = {
                        CONF_NWC_URI: nwc_info.raw_uri,
                        CONF_CONNECTION_NAME: (
                            user_input.get(CONF_CONNECTION_NAME, "").strip()
                            or DEFAULT_CONNECTION_NAME
                        ),
                        CONF_HUB_URL: hub_url,
                        CONF_LIGHTNING_ADDRESS: _resolve_lightning_address(user_input, nwc_info),
                        CONF_PRICE_PROVIDER: user_input[CONF_PRICE_PROVIDER],
                        CONF_PRICE_CURRENCY: user_input[CONF_PRICE_CURRENCY],
                        CONF_NETWORK_PROVIDER: user_input[CONF_NETWORK_PROVIDER],
                        CONF_NETWORK_API_BASE: user_input.get(CONF_NETWORK_API_BASE),
                        CONF_PREFER_LOCAL_RELAY: user_input[CONF_PREFER_LOCAL_RELAY],
                        **nostr_data,
                    }
                    if relay_override:
                        new_data[CONF_RELAY_OVERRIDE] = relay_override
                    nostr_enabled = bool(user_input.get(CONF_NOSTR_ENABLED, False))
                    bot_nsec_input = (user_input.get(CONF_NOSTR_BOT_NSEC, "") or "").strip()
                    if nostr_enabled and not bot_nsec_input:
                        generated_nsec, generated_npub = _generate_nostr_bot_keys()
                        new_data[CONF_NOSTR_BOT_NSEC] = generated_nsec
                        new_data[CONF_NOSTR_BOT_NPUB] = generated_npub
                        self._pending_data = new_data
                        self._generated_nsec = generated_nsec
                        self._generated_npub = generated_npub
                        return await self.async_step_nostr_keygen()
                    return self.async_create_entry(title="", data=new_data)

        return self.async_show_form(
            step_id="expert",
            data_schema=_expert_schema(_merged_entry_data(self.config_entry)),
            errors=errors,
            description_placeholders=placeholders,
        )

    async def async_step_nostr_keygen(self, user_input=None):
        """Display generated Nostr bot keys and require the user to confirm they are saved."""
        errors: dict[str, str] = {}
        if user_input is not None:
            if user_input.get("keys_saved"):
                return self.async_create_entry(title="", data=self._pending_data)
            errors["keys_saved"] = "keys_not_saved"

        return self.async_show_form(
            step_id="nostr_keygen",
            data_schema=vol.Schema({vol.Required("keys_saved", default=False): bool}),
            errors=errors,
            description_placeholders={
                "npub": self._generated_npub,
                "nsec": self._generated_nsec,
            },
        )


# ── Schema helpers ─────────────────────────────────────────────────────────


def _merged_entry_data(entry: config_entries.ConfigEntry) -> dict:
    """Merge entry.options over entry.data so options-flow defaults are current values."""
    merged = dict(entry.data)
    merged.update(entry.options)
    return merged


def _cloud_schema(user_input) -> vol.Schema:
    default_uri = ""
    default_connection_name = DEFAULT_CONNECTION_NAME
    default_warning = False
    default_price_provider = DEFAULT_PRICE_PROVIDER
    default_price_currency = DEFAULT_PRICE_CURRENCY
    default_network_provider = DEFAULT_NETWORK_PROVIDER
    default_network_api_base = ""
    default_lightning_address = ""
    default_nostr_enabled = False
    default_nostr_relays: list[str] = list(DEFAULT_NOSTR_RELAYS)
    default_nostr_bot_nsec = ""
    default_nostr_bot_npub = ""
    default_nostr_allowed_npubs = ""
    default_nostr_webhook_secret = ""
    if user_input:
        default_uri = user_input.get(CONF_NWC_URI, "")
        default_connection_name = user_input.get(CONF_CONNECTION_NAME, DEFAULT_CONNECTION_NAME)
        default_warning = user_input.get(CONF_ALLOW_CONTINUE_WITH_WARNING, False)
        default_price_provider = user_input.get(CONF_PRICE_PROVIDER, DEFAULT_PRICE_PROVIDER)
        default_price_currency = user_input.get(CONF_PRICE_CURRENCY, DEFAULT_PRICE_CURRENCY)
        default_network_provider = user_input.get(CONF_NETWORK_PROVIDER, DEFAULT_NETWORK_PROVIDER)
        default_network_api_base = user_input.get(CONF_NETWORK_API_BASE, "")
        default_lightning_address = user_input.get(CONF_LIGHTNING_ADDRESS, "") or ""
        default_nostr_enabled = bool(user_input.get(CONF_NOSTR_ENABLED, False))
        default_nostr_relays = _coerce_relay_list(user_input, default_nostr_relays)
        default_nostr_bot_nsec = user_input.get(CONF_NOSTR_BOT_NSEC, "")
        default_nostr_bot_npub = user_input.get(CONF_NOSTR_BOT_NPUB, "")
        default_nostr_allowed_npubs = user_input.get(CONF_NOSTR_ALLOWED_NPUBS, "")
        default_nostr_webhook_secret = user_input.get(CONF_NOSTR_WEBHOOK_SECRET, "")
    # Derive NPUB from NSEC if NSEC is present but NPUB is missing (user provided own NSEC)
    if default_nostr_bot_nsec and not default_nostr_bot_npub:
        default_nostr_bot_npub = _derive_npub_from_nsec(str(default_nostr_bot_nsec))

    return vol.Schema(
        {
            vol.Required(CONF_NWC_URI, default=default_uri): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_CONNECTION_NAME, default=default_connection_name): str,
            vol.Optional(CONF_LIGHTNING_ADDRESS, default=default_lightning_address): str,
            vol.Optional(CONF_PRICE_PROVIDER, default=default_price_provider): _price_provider_selector(),
            vol.Optional(CONF_PRICE_CURRENCY, default=default_price_currency): _currency_selector(),
            vol.Optional(CONF_NETWORK_PROVIDER, default=default_network_provider): _network_provider_selector(),
            vol.Optional(CONF_NETWORK_API_BASE, default=default_network_api_base): str,
            vol.Optional(CONF_NOSTR_ENABLED, default=default_nostr_enabled): bool,
            vol.Optional(CONF_NOSTR_RELAYS, default=default_nostr_relays): _nostr_relay_selector(),
            vol.Optional(CONF_NOSTR_BOT_NSEC, default=default_nostr_bot_nsec): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_NOSTR_BOT_NPUB, default=default_nostr_bot_npub): str,
            vol.Optional(CONF_NOSTR_ALLOWED_NPUBS, default=default_nostr_allowed_npubs): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
            vol.Optional(CONF_NOSTR_WEBHOOK_SECRET, default=default_nostr_webhook_secret): str,
            vol.Optional(CONF_ALLOW_CONTINUE_WITH_WARNING, default=default_warning): bool,
        }
    )


def _expert_schema(user_input) -> vol.Schema:
    default_uri = ""
    default_connection_name = DEFAULT_CONNECTION_NAME
    default_hub_url = DEFAULT_HUB_URL
    default_prefer_local_relay = True
    default_warning = False
    default_price_provider = DEFAULT_PRICE_PROVIDER
    default_price_currency = DEFAULT_PRICE_CURRENCY
    default_network_provider = DEFAULT_NETWORK_PROVIDER
    default_network_api_base = ""
    default_lightning_address = ""
    default_nostr_enabled = False
    default_nostr_relays: list[str] = list(DEFAULT_NOSTR_RELAYS)
    default_nostr_bot_nsec = ""
    default_nostr_bot_npub = ""
    default_nostr_allowed_npubs = ""
    default_nostr_webhook_secret = ""

    if user_input:
        default_uri = user_input.get(CONF_NWC_URI, "")
        default_connection_name = user_input.get(CONF_CONNECTION_NAME, DEFAULT_CONNECTION_NAME)
        default_hub_url = user_input.get(CONF_HUB_URL, DEFAULT_HUB_URL)
        default_prefer_local_relay = user_input.get(CONF_PREFER_LOCAL_RELAY, True)
        default_warning = user_input.get(CONF_ALLOW_CONTINUE_WITH_WARNING, False)
        default_price_provider = user_input.get(CONF_PRICE_PROVIDER, DEFAULT_PRICE_PROVIDER)
        default_price_currency = user_input.get(CONF_PRICE_CURRENCY, DEFAULT_PRICE_CURRENCY)
        default_network_provider = user_input.get(CONF_NETWORK_PROVIDER, DEFAULT_NETWORK_PROVIDER)
        default_network_api_base = user_input.get(CONF_NETWORK_API_BASE, "")
        default_lightning_address = user_input.get(CONF_LIGHTNING_ADDRESS, "") or ""
        default_nostr_enabled = bool(user_input.get(CONF_NOSTR_ENABLED, False))
        default_nostr_relays = _coerce_relay_list(user_input, default_nostr_relays)
        default_nostr_bot_nsec = user_input.get(CONF_NOSTR_BOT_NSEC, "")
        default_nostr_bot_npub = user_input.get(CONF_NOSTR_BOT_NPUB, "")
        default_nostr_allowed_npubs = user_input.get(CONF_NOSTR_ALLOWED_NPUBS, "")
        default_nostr_webhook_secret = user_input.get(CONF_NOSTR_WEBHOOK_SECRET, "")
    # Derive NPUB from NSEC if NSEC is present but NPUB is missing (user provided own NSEC)
    if default_nostr_bot_nsec and not default_nostr_bot_npub:
        default_nostr_bot_npub = _derive_npub_from_nsec(str(default_nostr_bot_nsec))

    return vol.Schema(
        {
            vol.Required(CONF_NWC_URI, default=default_uri): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_CONNECTION_NAME, default=default_connection_name): str,
            vol.Optional(CONF_HUB_URL, default=default_hub_url): str,
            vol.Optional(CONF_PREFER_LOCAL_RELAY, default=default_prefer_local_relay): bool,
            vol.Optional(CONF_LIGHTNING_ADDRESS, default=default_lightning_address): str,
            vol.Optional(CONF_PRICE_PROVIDER, default=default_price_provider): _price_provider_selector(),
            vol.Optional(CONF_PRICE_CURRENCY, default=default_price_currency): _currency_selector(),
            vol.Optional(CONF_NETWORK_PROVIDER, default=default_network_provider): _network_provider_selector(),
            vol.Optional(CONF_NETWORK_API_BASE, default=default_network_api_base): str,
            vol.Optional(CONF_NOSTR_ENABLED, default=default_nostr_enabled): bool,
            vol.Optional(CONF_NOSTR_RELAYS, default=default_nostr_relays): _nostr_relay_selector(),
            vol.Optional(CONF_NOSTR_BOT_NSEC, default=default_nostr_bot_nsec): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_NOSTR_BOT_NPUB, default=default_nostr_bot_npub): str,
            vol.Optional(CONF_NOSTR_ALLOWED_NPUBS, default=default_nostr_allowed_npubs): selector.TextSelector(
                selector.TextSelectorConfig(multiline=True)
            ),
            vol.Optional(CONF_NOSTR_WEBHOOK_SECRET, default=default_nostr_webhook_secret): str,
            vol.Optional(CONF_ALLOW_CONTINUE_WITH_WARNING, default=default_warning): bool,
        }
    )


# ── Helpers ────────────────────────────────────────────────────────────────


def _warnings_from_scope_result(scope_result: ScopeValidationResult) -> list[str]:
    warnings: list[str] = []
    if not scope_result.scope_info_available:
        warnings.append("Could not verify scopes from NWC URI")
    elif scope_result.missing_required:
        warnings.append(
            "Missing required scopes: " + ", ".join(sorted(scope_result.missing_required))
        )

    if scope_result.missing_optional:
        warnings.append(
            "Missing optional scopes: " + ", ".join(sorted(scope_result.missing_optional))
        )

    return warnings


def _build_local_relay(hub_url: str) -> str | None:
    parsed = urlparse(hub_url)
    if not parsed.scheme or not parsed.hostname:
        parsed = urlparse(f"http://{hub_url}")

    if not parsed.hostname:
        return None

    if parsed.scheme == "https":
        scheme = "wss"
    elif parsed.scheme == "http":
        scheme = "ws"
    else:
        return None

    return f"{scheme}://{parsed.hostname}:{RELAY_PROXY_PORT}"


def _resolve_lightning_address(user_input: dict, nwc_info: NwcConnectionInfo) -> str | None:
    manual = user_input.get(CONF_LIGHTNING_ADDRESS, "").strip()
    if manual:
        return manual
    parsed_lud16 = (nwc_info.lud16 or "").strip()
    return parsed_lud16 or None


def _normalize_nostr_config(user_input: dict, errors: dict[str, str]) -> dict[str, str | bool | list] | None:
    enabled = bool(user_input.get(CONF_NOSTR_ENABLED, False))
    relay_list = _coerce_relay_list(user_input, [])
    bot_nsec = (user_input.get(CONF_NOSTR_BOT_NSEC, "") or "").strip()
    bot_npub = (user_input.get(CONF_NOSTR_BOT_NPUB, "") or "").strip()
    allowed_npubs = (user_input.get(CONF_NOSTR_ALLOWED_NPUBS, "") or "").strip()
    webhook_secret = (user_input.get(CONF_NOSTR_WEBHOOK_SECRET, "") or "").strip()

    if enabled:
        # Derive NPUB from NSEC when user provides their own NSEC without NPUB
        if bot_nsec and not bot_npub:
            bot_npub = _derive_npub_from_nsec(bot_nsec)
        if not relay_list:
            errors[CONF_NOSTR_RELAYS] = "required"
        # Only require allowed_npubs when the user has provided their own key.
        # When bot_nsec is empty, the caller redirects to the keygen step first;
        # the user can fill in allowed_npubs via the options flow afterwards.
        if bot_nsec and not allowed_npubs:
            errors[CONF_NOSTR_ALLOWED_NPUBS] = "required"
        if errors:
            return None
        if not webhook_secret:
            # 24 random bytes produce 32 URL-safe chars and are sufficient entropy
            # for bearer-style webhook shared-secret protection.
            webhook_secret = secrets.token_urlsafe(24)

    return {
        CONF_NOSTR_ENABLED: enabled,
        CONF_NOSTR_RELAYS: relay_list,
        CONF_NOSTR_BOT_NSEC: bot_nsec,
        CONF_NOSTR_BOT_NPUB: bot_npub,
        CONF_NOSTR_ALLOWED_NPUBS: allowed_npubs,
        CONF_NOSTR_WEBHOOK_SECRET: webhook_secret,
    }


def _derive_npub_from_nsec(bot_nsec: str) -> str:
    try:
        return npub_from_nsec(bot_nsec)
    except ValueError:
        return ""


def _generate_nostr_bot_keys() -> tuple[str, str]:
    bot_nsec = nsec_from_hex(secrets.token_hex(32))
    bot_npub = npub_from_nsec(bot_nsec)
    return bot_nsec, bot_npub


def _ensure_bot_keys(enabled: bool, bot_nsec: str, bot_npub: str) -> tuple[str, str]:
    if not enabled:
        return bot_nsec, bot_npub
    if not bot_nsec:
        return _generate_nostr_bot_keys()
    if not bot_npub:
        return bot_nsec, _derive_npub_from_nsec(bot_nsec)
    return bot_nsec, bot_npub


def _coerce_relay_list(data: dict, fallback: list[str]) -> list[str]:
    """Return a deduplicated list of relay URLs from *data*.

    Handles both the new ``nostr_relays`` list field and the legacy
    ``nostr_relay`` single-string field for backward compatibility.
    """
    # New multi-relay field (list returned by the SelectSelector)
    relays = data.get(CONF_NOSTR_RELAYS)
    if isinstance(relays, list):
        cleaned = [r.strip() for r in relays if r and r.strip()]
        if cleaned:
            # Deduplicate while preserving order
            seen: set[str] = set()
            result: list[str] = []
            for r in cleaned:
                if r not in seen:
                    seen.add(r)
                    result.append(r)
            return result

    # Legacy single-relay field
    legacy = (data.get(CONF_NOSTR_RELAY) or "").strip()
    if legacy:
        return [legacy]

    return fallback
