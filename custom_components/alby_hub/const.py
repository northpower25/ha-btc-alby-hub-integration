"""Constants for the Alby Hub integration."""

from __future__ import annotations

DOMAIN = "alby_hub"

CONF_ALLOW_CONTINUE_WITH_WARNING = "allow_continue_with_warning"
CONF_HUB_URL = "hub_url"
CONF_MODE = "mode"
CONF_NWC_URI = "nwc_uri"
CONF_PREFER_LOCAL_RELAY = "prefer_local_relay"
CONF_RELAY_OVERRIDE = "relay_override"
CONF_SETUP_WARNINGS = "setup_warnings"

MODE_CLOUD = "cloud"
MODE_EXPERT = "expert"

DEFAULT_HUB_URL = "http://localhost:8080"
RELAY_PROXY_PORT = 3334

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
