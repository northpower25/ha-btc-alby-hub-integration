"""NWC parsing and validation helpers."""

from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import parse_qs, urlparse

from .const import OPTIONAL_NWC_SCOPES, REQUIRED_NWC_SCOPES

_SCOPE_KEYS = ("permissions", "scopes", "commands")
_LIGHTNING_ADDRESS_KEYS = ("lud16", "lightning_address", "lnaddress", "ln_addr")


@dataclass(slots=True, frozen=True)
class NwcConnectionInfo:
    """Parsed NWC connection information."""

    raw_uri: str
    wallet_pubkey: str
    relay: str
    secret: str
    lud16: str | None
    declared_scopes: set[str]


@dataclass(slots=True)
class ScopeValidationResult:
    """Result of NWC scope validation."""

    missing_required: set[str]
    missing_optional: set[str]
    scope_info_available: bool


def parse_nwc_connection_uri(uri: str) -> NwcConnectionInfo:
    """Parse a NWC URI and return structured metadata."""
    normalized_uri = uri.strip()
    parsed = urlparse(normalized_uri)
    if parsed.scheme != "nostr+walletconnect":
        raise ValueError("invalid_scheme")

    wallet_pubkey = parsed.netloc.strip()
    if not wallet_pubkey:
        raise ValueError("missing_wallet_pubkey")

    params = parse_qs(parsed.query, keep_blank_values=False)
    if parsed.fragment and "=" in parsed.fragment:
        fragment_params = parse_qs(parsed.fragment, keep_blank_values=False)
        for key, values in fragment_params.items():
            params.setdefault(key, []).extend(values)
    lowered_params = {str(k).lower(): v for k, v in params.items()}

    relay = _first_param(lowered_params, "relay")
    if not relay:
        raise ValueError("missing_relay")

    secret = _first_param(lowered_params, "secret")
    if not secret:
        raise ValueError("missing_secret")

    lud16 = _first_param(lowered_params, *_LIGHTNING_ADDRESS_KEYS)

    scopes: set[str] = set()
    for key in _SCOPE_KEYS:
        for raw_value in lowered_params.get(key, []):
            scopes.update(_split_scope_values(raw_value))

    return NwcConnectionInfo(
        raw_uri=normalized_uri,
        wallet_pubkey=wallet_pubkey,
        relay=relay,
        secret=secret,
        lud16=lud16,
        declared_scopes=scopes,
    )


def validate_scopes(info: NwcConnectionInfo) -> ScopeValidationResult:
    """Validate NWC scopes against integration requirements."""
    if not info.declared_scopes:
        return ScopeValidationResult(
            missing_required=set(REQUIRED_NWC_SCOPES),
            missing_optional=set(OPTIONAL_NWC_SCOPES),
            scope_info_available=False,
        )

    missing_required = set(REQUIRED_NWC_SCOPES) - info.declared_scopes
    missing_optional = set(OPTIONAL_NWC_SCOPES) - info.declared_scopes
    return ScopeValidationResult(
        missing_required=missing_required,
        missing_optional=missing_optional,
        scope_info_available=True,
    )


def _first_param(params: dict[str, list[str]], *keys: str) -> str | None:
    for key in keys:
        values = params.get(key.lower())
        if not values:
            continue
        value = values[0].strip()
        if value:
            return value
    return None


def _split_scope_values(raw_value: str) -> set[str]:
    values: set[str] = set()
    for scope in raw_value.replace(";", ",").replace(" ", ",").split(","):
        cleaned = scope.strip()
        if cleaned:
            values.add(cleaned)
    return values
