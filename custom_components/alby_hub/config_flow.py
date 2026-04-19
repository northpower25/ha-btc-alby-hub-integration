"""Config flow for Alby Hub integration."""

from __future__ import annotations

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
    CONF_MODE,
    CONF_NETWORK_API_BASE,
    CONF_NETWORK_PROVIDER,
    CONF_NWC_URI,
    CONF_PREFER_LOCAL_RELAY,
    CONF_PRICE_CURRENCY,
    CONF_PRICE_PROVIDER,
    CONF_RELAY_OVERRIDE,
    CONF_SETUP_WARNINGS,
    DEFAULT_CONNECTION_NAME,
    DEFAULT_NETWORK_PROVIDER,
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
from .nwc import ScopeValidationResult, parse_nwc_connection_uri, validate_scopes


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


class AlbyHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alby Hub."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> "AlbyHubOptionsFlowHandler":
        """Return the options flow handler (gear icon)."""
        return AlbyHubOptionsFlowHandler(config_entry)

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
                    await self.async_set_unique_id(f"{nwc_info.wallet_pubkey}:{nwc_info.relay}")
                    self._abort_if_unique_id_configured()
                    connection_name = (
                        user_input.get(CONF_CONNECTION_NAME, "").strip()
                        or DEFAULT_CONNECTION_NAME
                    )
                    return self.async_create_entry(
                        title=connection_name,
                        data={
                            CONF_MODE: MODE_CLOUD,
                            CONF_NWC_URI: nwc_info.raw_uri,
                            CONF_CONNECTION_NAME: connection_name,
                            CONF_PRICE_PROVIDER: user_input[CONF_PRICE_PROVIDER],
                            CONF_PRICE_CURRENCY: user_input[CONF_PRICE_CURRENCY],
                            CONF_NETWORK_PROVIDER: user_input[CONF_NETWORK_PROVIDER],
                            CONF_NETWORK_API_BASE: user_input.get(CONF_NETWORK_API_BASE),
                            CONF_SETUP_WARNINGS: warnings,
                        },
                    )

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
                    await self.async_set_unique_id(f"{nwc_info.wallet_pubkey}:{hub_url}")
                    self._abort_if_unique_id_configured()
                    connection_name = (
                        user_input.get(CONF_CONNECTION_NAME, "").strip()
                        or DEFAULT_CONNECTION_NAME
                    )
                    data = {
                        CONF_MODE: MODE_EXPERT,
                        CONF_NWC_URI: nwc_info.raw_uri,
                        CONF_CONNECTION_NAME: connection_name,
                        CONF_HUB_URL: hub_url,
                        CONF_PRICE_PROVIDER: user_input[CONF_PRICE_PROVIDER],
                        CONF_PRICE_CURRENCY: user_input[CONF_PRICE_CURRENCY],
                        CONF_NETWORK_PROVIDER: user_input[CONF_NETWORK_PROVIDER],
                        CONF_NETWORK_API_BASE: user_input.get(CONF_NETWORK_API_BASE),
                        CONF_SETUP_WARNINGS: warnings,
                        CONF_PREFER_LOCAL_RELAY: user_input[CONF_PREFER_LOCAL_RELAY],
                    }
                    if relay_override:
                        data[CONF_RELAY_OVERRIDE] = relay_override
                    return self.async_create_entry(title=connection_name, data=data)

        return self.async_show_form(
            step_id="expert",
            data_schema=_expert_schema(user_input),
            errors=errors,
            description_placeholders=placeholders,
        )


class AlbyHubOptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options flow for Alby Hub (gear icon reconfiguration)."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        self._config_entry = config_entry

    async def async_step_init(self, user_input=None):
        """Route to the correct options step based on current mode."""
        mode = self._config_entry.data.get(CONF_MODE, MODE_CLOUD)
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
                    return self.async_create_entry(
                        title="",
                        data={
                            CONF_NWC_URI: nwc_info.raw_uri,
                            CONF_CONNECTION_NAME: (
                                user_input.get(CONF_CONNECTION_NAME, "").strip()
                                or DEFAULT_CONNECTION_NAME
                            ),
                            CONF_PRICE_PROVIDER: user_input[CONF_PRICE_PROVIDER],
                            CONF_PRICE_CURRENCY: user_input[CONF_PRICE_CURRENCY],
                            CONF_NETWORK_PROVIDER: user_input[CONF_NETWORK_PROVIDER],
                            CONF_NETWORK_API_BASE: user_input.get(CONF_NETWORK_API_BASE),
                        },
                    )

        return self.async_show_form(
            step_id="cloud",
            data_schema=_cloud_schema(_merged_entry_data(self._config_entry)),
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
                    new_data: dict = {
                        CONF_NWC_URI: nwc_info.raw_uri,
                        CONF_CONNECTION_NAME: (
                            user_input.get(CONF_CONNECTION_NAME, "").strip()
                            or DEFAULT_CONNECTION_NAME
                        ),
                        CONF_HUB_URL: hub_url,
                        CONF_PRICE_PROVIDER: user_input[CONF_PRICE_PROVIDER],
                        CONF_PRICE_CURRENCY: user_input[CONF_PRICE_CURRENCY],
                        CONF_NETWORK_PROVIDER: user_input[CONF_NETWORK_PROVIDER],
                        CONF_NETWORK_API_BASE: user_input.get(CONF_NETWORK_API_BASE),
                        CONF_PREFER_LOCAL_RELAY: user_input[CONF_PREFER_LOCAL_RELAY],
                    }
                    if relay_override:
                        new_data[CONF_RELAY_OVERRIDE] = relay_override
                    return self.async_create_entry(title="", data=new_data)

        return self.async_show_form(
            step_id="expert",
            data_schema=_expert_schema(_merged_entry_data(self._config_entry)),
            errors=errors,
            description_placeholders=placeholders,
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
    if user_input:
        default_uri = user_input.get(CONF_NWC_URI, "")
        default_connection_name = user_input.get(CONF_CONNECTION_NAME, DEFAULT_CONNECTION_NAME)
        default_warning = user_input.get(CONF_ALLOW_CONTINUE_WITH_WARNING, False)
        default_price_provider = user_input.get(CONF_PRICE_PROVIDER, DEFAULT_PRICE_PROVIDER)
        default_price_currency = user_input.get(CONF_PRICE_CURRENCY, DEFAULT_PRICE_CURRENCY)
        default_network_provider = user_input.get(CONF_NETWORK_PROVIDER, DEFAULT_NETWORK_PROVIDER)
        default_network_api_base = user_input.get(CONF_NETWORK_API_BASE, "")

    return vol.Schema(
        {
            vol.Required(CONF_NWC_URI, default=default_uri): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_CONNECTION_NAME, default=default_connection_name): str,
            vol.Optional(CONF_PRICE_PROVIDER, default=default_price_provider): _price_provider_selector(),
            vol.Optional(CONF_PRICE_CURRENCY, default=default_price_currency): _currency_selector(),
            vol.Optional(CONF_NETWORK_PROVIDER, default=default_network_provider): _network_provider_selector(),
            vol.Optional(CONF_NETWORK_API_BASE, default=default_network_api_base): str,
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

    return vol.Schema(
        {
            vol.Required(CONF_NWC_URI, default=default_uri): selector.TextSelector(
                selector.TextSelectorConfig(type=selector.TextSelectorType.PASSWORD)
            ),
            vol.Optional(CONF_CONNECTION_NAME, default=default_connection_name): str,
            vol.Optional(CONF_HUB_URL, default=default_hub_url): str,
            vol.Optional(CONF_PREFER_LOCAL_RELAY, default=default_prefer_local_relay): bool,
            vol.Optional(CONF_PRICE_PROVIDER, default=default_price_provider): _price_provider_selector(),
            vol.Optional(CONF_PRICE_CURRENCY, default=default_price_currency): _currency_selector(),
            vol.Optional(CONF_NETWORK_PROVIDER, default=default_network_provider): _network_provider_selector(),
            vol.Optional(CONF_NETWORK_API_BASE, default=default_network_api_base): str,
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
