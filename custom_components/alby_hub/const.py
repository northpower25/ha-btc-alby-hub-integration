"""Constants for the Alby Hub integration."""

from __future__ import annotations

DOMAIN = "alby_hub"

CONF_ALLOW_CONTINUE_WITH_WARNING = "allow_continue_with_warning"
CONF_HUB_URL = "hub_url"
CONF_MODE = "mode"
CONF_NETWORK_API_BASE = "network_api_base"
CONF_NETWORK_PROVIDER = "network_provider"
CONF_NWC_URI = "nwc_uri"
CONF_PREFER_LOCAL_RELAY = "prefer_local_relay"
CONF_PRICE_CURRENCY = "price_currency"
CONF_PRICE_PROVIDER = "price_provider"
CONF_RELAY_OVERRIDE = "relay_override"
CONF_SETUP_WARNINGS = "setup_warnings"

MODE_CLOUD = "cloud"
MODE_EXPERT = "expert"

DEFAULT_HUB_URL = "http://localhost:8080"
DEFAULT_NETWORK_PROVIDER = "mempool"
DEFAULT_PRICE_CURRENCY = "EUR"
DEFAULT_PRICE_PROVIDER = "coingecko"
RELAY_PROXY_PORT = 3334

NETWORK_PROVIDER_MEMPOOL = "mempool"
NETWORK_PROVIDER_CUSTOM_NODE = "custom_node"

PRICE_PROVIDER_BINANCE = "binance"
PRICE_PROVIDER_BITCOIN_DE = "bitcoin_de"
PRICE_PROVIDER_BITQUERY = "bitquery"
PRICE_PROVIDER_BLOCKCHAIN = "blockchain_com"
PRICE_PROVIDER_COINDESK = "coindesk"
PRICE_PROVIDER_COINGECKO = "coingecko"
PRICE_PROVIDER_COINBASE = "coinbase"
PRICE_PROVIDER_MEMPOOL = "mempool"

REQUIRED_NWC_SCOPES: tuple[str, ...] = (
    "get_info",
    "get_balance",
    "list_transactions",
    "make_invoice",
)
OPTIONAL_NWC_SCOPES: tuple[str, ...] = ("pay_invoice",)

SERVICE_CREATE_INVOICE = "create_invoice"
SERVICE_SEND_PAYMENT = "send_payment"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"

# Text entity keys (invoice workflow)
TEXT_KEY_INVOICE_INPUT = "invoice_input"
TEXT_KEY_LAST_INVOICE = "last_invoice"

# Satoshis per Bitcoin
SATS_PER_BTC = 100_000_000
