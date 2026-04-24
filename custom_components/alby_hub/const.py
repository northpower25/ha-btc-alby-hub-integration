"""Constants for the Alby Hub integration."""

from __future__ import annotations

DOMAIN = "alby_hub"

CONF_ALLOW_CONTINUE_WITH_WARNING = "allow_continue_with_warning"
CONF_CONNECTION_NAME = "connection_name"
CONF_HUB_URL = "hub_url"
CONF_LIGHTNING_ADDRESS = "lightning_address"
CONF_MODE = "mode"
CONF_NETWORK_API_BASE = "network_api_base"
CONF_NETWORK_PROVIDER = "network_provider"
CONF_NWC_URI = "nwc_uri"
CONF_PREFER_LOCAL_RELAY = "prefer_local_relay"
CONF_PRICE_CURRENCY = "price_currency"
CONF_PRICE_PROVIDER = "price_provider"
CONF_RELAY_OVERRIDE = "relay_override"
CONF_SETUP_WARNINGS = "setup_warnings"
CONF_NOSTR_ENABLED = "nostr_enabled"
CONF_NOSTR_RELAY = "nostr_relay"
CONF_NOSTR_RELAYS = "nostr_relays"
CONF_NOSTR_BOT_NSEC = "nostr_bot_nsec"
CONF_NOSTR_BOT_NPUB = "nostr_bot_npub"
CONF_NOSTR_ALLOWED_NPUBS = "nostr_allowed_npubs"
CONF_NOSTR_WEBHOOK_SECRET = "nostr_webhook_secret"
CONF_NOSTR_ENCRYPTION_MODE = "nostr_encryption_mode"

# Nostr encryption mode values
NOSTR_ENCRYPTION_NIP44 = "nip44"
NOSTR_ENCRYPTION_NIP04 = "nip04"
NOSTR_ENCRYPTION_BOTH = "both"
NOSTR_ENCRYPTION_PLAINTEXT = "plaintext"
DEFAULT_NOSTR_ENCRYPTION_MODE = NOSTR_ENCRYPTION_NIP04

MODE_CLOUD = "cloud"
MODE_EXPERT = "expert"

DEFAULT_CONNECTION_NAME = "Alby Hub"
DEFAULT_HUB_URL = "http://localhost:8080"
DEFAULT_NETWORK_PROVIDER = "mempool"
DEFAULT_PRICE_CURRENCY = "EUR"
DEFAULT_PRICE_PROVIDER = "coingecko"
DEFAULT_NOSTR_RELAY = "wss://relay.getalby.com/v1"
DEFAULT_NOSTR_RELAYS: list[str] = [
    "wss://relay.damus.io",
    "wss://relay.primal.net",
    "wss://nos.lol",
    "wss://relay.nostr.band",
    "wss://nostr.wine",
]
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
OPTIONAL_NWC_SCOPES: tuple[str, ...] = ("pay_invoice", "get_budget")

SERVICE_CREATE_INVOICE = "create_invoice"
SERVICE_SEND_PAYMENT = "send_payment"
SERVICE_LIST_TRANSACTIONS = "list_transactions"
SERVICE_SCHEDULE_PAYMENT = "schedule_payment"
SERVICE_LIST_SCHEDULED_PAYMENTS = "list_scheduled_payments"
SERVICE_DELETE_SCHEDULED_PAYMENT = "delete_scheduled_payment"
SERVICE_UPDATE_SCHEDULED_PAYMENT = "update_scheduled_payment"
SERVICE_RUN_SCHEDULED_PAYMENT_NOW = "run_scheduled_payment_now"
SERVICE_NOSTR_SEND_BOT_MESSAGE = "nostr_send_bot_message"
SERVICE_NOSTR_SEND_TEST_MESSAGE = "nostr_send_test_message"
SERVICE_NOSTR_LIST_MESSAGES = "nostr_list_messages"

ATTR_CONFIG_ENTRY_ID = "config_entry_id"

# Persistent storage key for recurring/scheduled payments
STORAGE_KEY_SCHEDULED_PAYMENTS = f"alby_hub_scheduled_payments"
STORAGE_VERSION_SCHEDULED_PAYMENTS = 1

# Text entity keys (invoice workflow)
TEXT_KEY_INVOICE_INPUT = "invoice_input"
TEXT_KEY_LAST_INVOICE = "last_invoice"

# Sensor key for last created invoice (stored as attribute to avoid 255-char state limit)
SENSOR_KEY_LAST_INVOICE = "last_invoice"

# Satoshis per Bitcoin
SATS_PER_BTC = 100_000_000

# Invoice workflow entity keys
NUMBER_KEY_INVOICE_AMOUNT = "invoice_amount"
SELECT_KEY_INVOICE_AMOUNT_UNIT = "invoice_amount_unit"
BUTTON_KEY_CREATE_INVOICE = "create_invoice_btn"

# NWC Budget sensor keys
SENSOR_KEY_NWC_BUDGET_TOTAL = "nwc_budget_total"
SENSOR_KEY_NWC_BUDGET_USED = "nwc_budget_used"
SENSOR_KEY_NWC_BUDGET_REMAINING = "nwc_budget_remaining"
SENSOR_KEY_NWC_BUDGET_RENEWAL = "nwc_budget_renewal"
SENSOR_KEY_API_DEBUG_STATUS = "api_debug_status"

# Common fiat currencies for the price_currency selector (sorted alphabetically)
COMMON_FIAT_CURRENCIES: list[str] = [
    "AED", "ARS", "AUD", "BRL", "CAD", "CHF", "CLP", "CNY", "CZK",
    "DKK", "EUR", "GBP", "HKD", "HUF", "IDR", "ILS", "INR", "JPY",
    "KRW", "MXN", "MYR", "NOK", "NZD", "PHP", "PLN", "RON", "RUB",
    "SAR", "SEK", "SGD", "THB", "TRY", "TWD", "UAH", "USD", "VND", "ZAR",
]
