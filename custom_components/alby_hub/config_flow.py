"""Config flow for Alby Hub integration."""

from __future__ import annotations

from urllib.parse import urlparse

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.helpers import selector
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import AlbyHubApiClient
from .const import (
    CONF_ALLOW_CONTINUE_WITH_WARNING,
    CONF_HUB_URL,
    CONF_MODE,
    CONF_NWC_URI,
    CONF_PREFER_LOCAL_RELAY,
    CONF_RELAY_OVERRIDE,
    CONF_SETUP_WARNINGS,
    DEFAULT_HUB_URL,
    DOMAIN,
    MODE_CLOUD,
    MODE_EXPERT,
    RELAY_PROXY_PORT,
)
from .nwc import ScopeValidationResult, parse_nwc_connection_uri, validate_scopes


class AlbyHubConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Alby Hub."""

    VERSION = 1

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
                    return self.async_create_entry(
                        title="Alby Hub",
                        data={
                            CONF_MODE: MODE_CLOUD,
                            CONF_NWC_URI: nwc_info.raw_uri,
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
                    warnings.append("local_api_unreachable")

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
                    data = {
                        CONF_MODE: MODE_EXPERT,
                        CONF_NWC_URI: nwc_info.raw_uri,
                        CONF_HUB_URL: hub_url,
                        CONF_SETUP_WARNINGS: warnings,
                        CONF_PREFER_LOCAL_RELAY: user_input[CONF_PREFER_LOCAL_RELAY],
                    }
                    if relay_override:
                        data[CONF_RELAY_OVERRIDE] = relay_override
                    return self.async_create_entry(title="Alby Hub", data=data)

        return self.async_show_form(
            step_id="expert",
            data_schema=_expert_schema(user_input),
            errors=errors,
            description_placeholders=placeholders,
        )


def _cloud_schema(user_input) -> vol.Schema:
    default_uri = ""
    default_warning = False
    if user_input:
        default_uri = user_input.get(CONF_NWC_URI, "")
        default_warning = user_input.get(CONF_ALLOW_CONTINUE_WITH_WARNING, False)

    return vol.Schema(
        {
            vol.Required(CONF_NWC_URI, default=default_uri): str,
            vol.Optional(
                CONF_ALLOW_CONTINUE_WITH_WARNING,
                default=default_warning,
            ): bool,
        }
    )


def _expert_schema(user_input) -> vol.Schema:
    default_uri = ""
    default_hub_url = DEFAULT_HUB_URL
    default_prefer_local_relay = True
    default_warning = False

    if user_input:
        default_uri = user_input.get(CONF_NWC_URI, "")
        default_hub_url = user_input.get(CONF_HUB_URL, DEFAULT_HUB_URL)
        default_prefer_local_relay = user_input.get(CONF_PREFER_LOCAL_RELAY, True)
        default_warning = user_input.get(CONF_ALLOW_CONTINUE_WITH_WARNING, False)

    return vol.Schema(
        {
            vol.Required(CONF_NWC_URI, default=default_uri): str,
            vol.Optional(CONF_HUB_URL, default=default_hub_url): str,
            vol.Optional(CONF_PREFER_LOCAL_RELAY, default=default_prefer_local_relay): bool,
            vol.Optional(
                CONF_ALLOW_CONTINUE_WITH_WARNING,
                default=default_warning,
            ): bool,
        }
    )


def _warnings_from_scope_result(scope_result: ScopeValidationResult) -> list[str]:
    warnings: list[str] = []
    if not scope_result.scope_info_available:
        warnings.append("scope_info_missing")
    elif scope_result.missing_required:
        warnings.append("missing_required_scopes: " + ", ".join(sorted(scope_result.missing_required)))

    if scope_result.missing_optional:
        warnings.append("missing_optional_scopes: " + ", ".join(sorted(scope_result.missing_optional)))

    return warnings


def _build_local_relay(hub_url: str) -> str | None:
    parsed = urlparse(hub_url)
    if not parsed.hostname:
        return None

    scheme = "wss" if parsed.scheme == "https" else "ws"
    return f"{scheme}://{parsed.hostname}:{RELAY_PROXY_PORT}"
