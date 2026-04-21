"""Data coordinator for Alby Hub."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from aiohttp import ClientError, ClientSession, ClientTimeout
from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AlbyHubApiClient, AlbyHubApiError
from .const import (
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
)
from .nwc import NwcConnectionInfo
from .nwc_client import async_nwc_request

_LOGGER = logging.getLogger(__name__)
_BALANCE_KEYS: tuple[str, ...] = ("balance", "sat", "sats", "total")
_HASHES_PER_EXAHASH = 1_000_000_000_000_000_000
_API_REQUEST_TIMEOUT_SECONDS = 5
_HALVING_INTERVAL_BLOCKS = 210000
_MINUTES_PER_BLOCK = 10
_MSATS_PER_SAT = 1000  # millisatoshis per satoshi
_DEFAULT_MEMPOOL_API = "https://mempool.space"


class AlbyHubDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch Alby Hub status for entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        mode: str,
        nwc_info: NwcConnectionInfo,
        api_client: AlbyHubApiClient | None,
        session: ClientSession,
        price_provider: str,
        price_currency: str,
        network_provider: str,
        network_api_base: str | None,
        entry_name: str,
        manual_lightning_address: str | None = None,
    ) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name="alby_hub",
            update_interval=timedelta(seconds=60),
        )
        self._mode = mode
        self._nwc_info = nwc_info
        self._api_client = api_client
        self._session = session
        self._price_provider = price_provider
        self._price_currency = price_currency.upper()
        self._network_provider = network_provider
        self._network_api_base = network_api_base
        self._entry_name = entry_name
        self._manual_lightning_address = manual_lightning_address

    async def _async_update_data(self) -> dict[str, Any]:
        lightning_address = _first_valid_lightning_address(
            # _first_valid_lightning_address returns the first non-empty value in argument order.
            # Manual value should therefore override URI-discovered lud16 when provided by user.
            self._manual_lightning_address,
            self._nwc_info.lud16,
        )
        data: dict[str, Any] = {
            "mode": self._mode,
            "entry_name": self._entry_name,
            "wallet_pubkey": self._nwc_info.wallet_pubkey,
            "relay": self._nwc_info.relay,
            # Prefer NWC-URI lud16; fall back to the manually configured address
            "lightning_address": lightning_address,
            "connected": self._mode != MODE_EXPERT,
            "balance_lightning": None,
            "balance_onchain": None,
            "bitcoin_block_height": None,
            "bitcoin_hashrate": None,
            "bitcoin_price": None,
            "blocks_until_halving": None,
            "minutes_per_block": _MINUTES_PER_BLOCK,
            "price_currency": self._price_currency,
            "version": None,
            "alias": None,
            "nwc_budget_total": None,
            "nwc_budget_used": None,
            "nwc_budget_remaining": None,
            "nwc_budget_renewal": None,
            "transactions": [],
        }

        if self._mode == MODE_EXPERT and self._api_client is not None:
            if not await self._api_client.health_check():
                data["connected"] = False
                return data

            try:
                info = await self._api_client.get_info()
                balance = await self._api_client.get_balance()
            except AlbyHubApiError as err:
                raise UpdateFailed(f"Failed to fetch expert-mode API data: {err}") from err

            data["connected"] = True
            data["version"] = info.get("version")
            data["alias"] = info.get("alias") or info.get("name")

            lightning = balance.get("lightning") if isinstance(balance, dict) else None
            onchain = balance.get("onchain") if isinstance(balance, dict) else None
            data["balance_lightning"] = _read_sat_value(lightning)
            data["balance_onchain"] = _read_sat_value(onchain)

            # Fetch recent transactions in expert mode
            try:
                txs = await self._api_client.list_transactions(limit=50)
                data["transactions"] = _normalize_transactions(txs)
            except AlbyHubApiError as err:
                _LOGGER.debug("Failed to fetch transactions (expert mode): %s", err)
        else:
            # Cloud / NWC-only mode: fetch balance and info via NWC protocol
            await self._fetch_nwc_data(data)

        data["bitcoin_price"] = await _fetch_bitcoin_price(
            self._session, self._price_provider, self._price_currency
        )
        network_stats = await _fetch_network_stats(
            self._session, self._network_provider, self._network_api_base
        )
        data.update(network_stats)

        return data

    async def _fetch_nwc_data(self, data: dict[str, Any]) -> None:
        """Fetch Lightning balance and hub info via NWC get_balance / get_info / get_budget.

        Updates *data* in-place.  All failures are silently logged at DEBUG
        level so that other sensors are not affected.
        """
        request_succeeded = False

        # get_balance → balance_lightning (NWC returns balance in millisatoshis)
        try:
            result = await async_nwc_request(self._session, self._nwc_info, "get_balance")
            if result is not None and result.get("error") is None:
                request_succeeded = True
                bal_result = result.get("result") or {}
                bal_sat = _extract_nwc_balance_sat(bal_result)
                if bal_sat is not None:
                    data["balance_lightning"] = bal_sat
        except Exception as err:
            _LOGGER.debug("NWC get_balance failed: %s", err)

        # get_info → version, and lightning_address fallback if not in URI
        try:
            result = await async_nwc_request(self._session, self._nwc_info, "get_info")
            if result is not None and result.get("error") is None:
                request_succeeded = True
                info_result = result.get("result") or {}
                version = info_result.get("version")
                if version:
                    data["version"] = str(version)
                if _is_missing_lightning_address(data.get("lightning_address")):
                    lud16 = info_result.get("lud16") or info_result.get("lightning_address")
                    if not _is_missing_lightning_address(lud16):
                        data["lightning_address"] = str(lud16).strip()
                    elif self._manual_lightning_address:
                        data["lightning_address"] = self._manual_lightning_address
        except Exception as err:
            _LOGGER.debug("NWC get_info failed: %s", err)

        # get_budget → NWC spending limits (optional, not supported by all implementations)
        try:
            result = await async_nwc_request(self._session, self._nwc_info, "get_budget")
            if result is not None and result.get("error") is None:
                request_succeeded = True
                budget_result = result.get("result") or {}
                total_msat = (
                    budget_result.get("total_budget")
                    or budget_result.get("budget")
                    or budget_result.get("limit")
                )
                used_msat = (
                    budget_result.get("used_budget")
                    or budget_result.get("used")
                    or budget_result.get("spent")
                )
                renewal = (
                    budget_result.get("renewal_period")
                    or budget_result.get("renewal")
                    or budget_result.get("period")
                )
                if isinstance(used_msat, (int, float)):
                    data["nwc_budget_used"] = int(int(used_msat) // _MSATS_PER_SAT)
                if isinstance(total_msat, (int, float)):
                    total_sat = int(int(total_msat) // _MSATS_PER_SAT)
                    data["nwc_budget_total"] = total_sat
                    if data["nwc_budget_used"] is not None:
                        data["nwc_budget_remaining"] = max(
                            0, total_sat - data["nwc_budget_used"]
                        )
                if isinstance(renewal, str) and renewal:
                    data["nwc_budget_renewal"] = renewal
        except Exception as err:
            _LOGGER.debug("NWC get_budget failed: %s", err)

        # list_transactions → recent payment history
        try:
            # Include unpaid invoices so newly created receive requests also appear in Activity.
            result = await async_nwc_request(
                self._session, self._nwc_info, "list_transactions",
                {"limit": 50, "unpaid": True},
            )
            if result is not None and result.get("error") is None:
                request_succeeded = True
                tx_result = result.get("result") or {}
                raw_txs = (
                    tx_result
                    if isinstance(tx_result, list)
                    else (tx_result.get("transactions") or tx_result.get("data") or [])
                )
                data["transactions"] = _normalize_transactions(raw_txs)
        except Exception as err:
            _LOGGER.debug("NWC list_transactions failed: %s", err)

        data["connected"] = request_succeeded


def _read_sat_value(value: Any) -> int | None:
    """Read satoshi-like values from known Alby API balance shapes."""
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, dict):
        for key in _BALANCE_KEYS:
            nested = value.get(key)
            if isinstance(nested, (int, float)):
                return int(nested)
    return None


async def _fetch_bitcoin_price(
    session: ClientSession, provider: str, currency: str
) -> float | None:
    provider_chain: list[str] = [provider]
    fallback_providers = (
        PRICE_PROVIDER_COINGECKO,
        PRICE_PROVIDER_COINBASE,
        PRICE_PROVIDER_MEMPOOL,
        PRICE_PROVIDER_BLOCKCHAIN,
        PRICE_PROVIDER_BINANCE,
    )
    for fallback in fallback_providers:
        if fallback not in provider_chain:
            provider_chain.append(fallback)

    for candidate in provider_chain:
        price = await _fetch_bitcoin_price_from_provider(session, candidate, currency)
        if price is not None:
            return price
    return None


async def _fetch_network_stats(
    session: ClientSession, provider: str, api_base: str | None
) -> dict[str, int | float | None]:
    if provider not in (NETWORK_PROVIDER_MEMPOOL, NETWORK_PROVIDER_CUSTOM_NODE):
        return _empty_network_payload()

    if provider == NETWORK_PROVIDER_CUSTOM_NODE and api_base:
        custom_base = api_base.rstrip("/")
        stats = await _fetch_network_stats_from_base(session, custom_base)
        if stats["bitcoin_block_height"] is not None:
            return stats
        _LOGGER.debug(
            "Custom network provider did not return valid data; falling back to %s",
            _DEFAULT_MEMPOOL_API,
        )

    return await _fetch_network_stats_from_base(session, _DEFAULT_MEMPOOL_API)


def _empty_network_payload() -> dict[str, None | float]:
    return {
        "bitcoin_block_height": None,
        "bitcoin_hashrate": None,
        "blocks_until_halving": None,
        "minutes_per_block": _MINUTES_PER_BLOCK,
    }


async def _fetch_bitcoin_price_from_provider(
    session: ClientSession, provider: str, currency: str
) -> float | None:
    try:
        if provider == PRICE_PROVIDER_COINGECKO:
            data = await _safe_get_json(
                session,
                f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={currency.lower()}",
            )
            value = data.get("bitcoin", {}).get(currency.lower()) if isinstance(data, dict) else None
            return float(value) if value is not None else None

        if provider == PRICE_PROVIDER_COINBASE:
            data = await _safe_get_json(
                session, f"https://api.coinbase.com/v2/prices/BTC-{currency}/spot"
            )
            amount = data.get("data", {}).get("amount") if isinstance(data, dict) else None
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_BINANCE:
            data = await _safe_get_json(
                session, f"https://api.binance.com/api/v3/ticker/price?symbol=BTC{currency}"
            )
            amount = data.get("price") if isinstance(data, dict) else None
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_BLOCKCHAIN:
            data = await _safe_get_json(session, "https://blockchain.info/ticker")
            amount = data.get(currency, {}).get("last") if isinstance(data, dict) else None
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_COINDESK:
            _LOGGER.debug("CoinDesk v1 API is no longer available; trying fallback provider")
            return None

        if provider == PRICE_PROVIDER_MEMPOOL:
            data = await _safe_get_json(session, f"{_DEFAULT_MEMPOOL_API}/api/v1/prices")
            amount = data.get(currency) if isinstance(data, dict) else None
            if amount is None:
                _LOGGER.debug(
                    "Mempool price API did not return data for currency %s; available keys: %s",
                    currency,
                    list(data.keys()) if isinstance(data, dict) else data,
                )
            return float(amount) if amount is not None else None

        if provider in (PRICE_PROVIDER_BITCOIN_DE, PRICE_PROVIDER_BITQUERY):
            _LOGGER.debug("Price provider %s is not implemented; trying fallback provider", provider)
            return None
    except (TypeError, ValueError):
        return None

    return None


async def _fetch_network_stats_from_base(
    session: ClientSession, base_url: str
) -> dict[str, int | float | None]:
    height_data = await _safe_get_json(session, f"{base_url}/api/blocks/tip/height")
    hashrate_data = await _safe_get_json(session, f"{base_url}/api/v1/mining/hashrate/3d")

    if not isinstance(height_data, int):
        _LOGGER.debug(
            "Network stats: block height endpoint returned unexpected data: %r (base_url=%s)",
            height_data,
            base_url,
        )
        return _empty_network_payload()

    hashrate = None
    minutes_per_block = _MINUTES_PER_BLOCK
    if isinstance(hashrate_data, dict):
        current = hashrate_data.get("currentHashrate")
        if isinstance(current, (int, float)):
            hashrate = round(float(current) / _HASHES_PER_EXAHASH, 2)
        avg_block_time_seconds = hashrate_data.get("avgBlockTime")
        if isinstance(avg_block_time_seconds, (int, float)) and avg_block_time_seconds > 0:
            minutes_per_block = float(avg_block_time_seconds) / 60

    next_halving_height = _calculate_next_halving_height(height_data)
    blocks_until_halving = max(next_halving_height - height_data, 0)

    return {
        "bitcoin_block_height": height_data,
        "bitcoin_hashrate": hashrate,
        "blocks_until_halving": blocks_until_halving,
        "minutes_per_block": minutes_per_block,
    }


def _extract_nwc_balance_sat(balance_result: Any) -> int | None:
    if not isinstance(balance_result, dict):
        return None

    msat_keys = ("balance", "balance_msat", "msats", "msat", "total_msat")
    for key in msat_keys:
        value = balance_result.get(key)
        if isinstance(value, (int, float)):
            return int(value) // _MSATS_PER_SAT

    sat_keys = ("balance_sat", "sat", "sats", "total")
    for key in sat_keys:
        value = balance_result.get(key)
        if isinstance(value, (int, float)):
            return int(value)

    return None


def _is_missing_lightning_address(value: Any) -> bool:
    if value is None:
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"unknown", "unavailable", "none", "null", "n/a", "na"}


def _first_valid_lightning_address(*values: Any) -> str | None:
    for value in values:
        if not _is_missing_lightning_address(value):
            return str(value).strip()
    return None


async def _safe_get_json(session: ClientSession, url: str) -> Any:
    try:
        async with session.get(url, timeout=ClientTimeout(total=_API_REQUEST_TIMEOUT_SECONDS)) as response:
            if response.status >= 400:
                _LOGGER.debug("HTTP %s fetching %s", response.status, url)
                return None
            content_type = response.headers.get("Content-Type", "").lower()
            if "json" in content_type:
                return await response.json(content_type=None)
            raw_text = (await response.text()).strip()
            if raw_text:
                try:
                    return int(raw_text)
                except ValueError:
                    pass
            try:
                return await response.json(content_type=None)
            except ValueError:
                return raw_text or None
    except TimeoutError:
        _LOGGER.debug("Timeout fetching %s", url)
        return None
    except (ClientError, ValueError) as err:
        _LOGGER.debug("Error fetching %s: %s", url, err)
        return None


def _calculate_next_halving_height(current_height: int) -> int:
    return ((current_height // _HALVING_INTERVAL_BLOCKS) + 1) * _HALVING_INTERVAL_BLOCKS


def _normalize_transactions(raw: Any) -> list[dict[str, Any]]:
    """Normalize a list of transaction dicts from either the local API or NWC.

    Produces a consistent shape:
        type        : "incoming" | "outgoing"
        amount_sat  : int
        fees_sat    : int
        description : str
        settled_at  : int | None  (Unix timestamp)
        created_at  : int | None
        payment_hash: str
        settled     : bool
    """
    if not isinstance(raw, list):
        # Some API shapes wrap the list: {"transactions": [...]} or {"data": [...]}
        if isinstance(raw, dict):
            raw = raw.get("transactions") or raw.get("data") or raw.get("items") or []
        else:
            return []

    result: list[dict[str, Any]] = []
    for tx in raw:
        if not isinstance(tx, dict):
            continue
        raw_type = str(tx.get("type", "incoming")).lower()
        if raw_type in {"incoming", "receive", "in", "credit", "incoming_payment"}:
            tx_type = "incoming"
        elif raw_type in {"outgoing", "send", "out", "debit", "outgoing_payment"}:
            tx_type = "outgoing"
        else:
            tx_type = "incoming" if bool(tx.get("incoming")) else "outgoing"

        amount_sat: int = 0
        amount_msat = tx.get("amount_msat") or tx.get("msat") or tx.get("msats")
        amount_direct = tx.get("amount") or tx.get("value")
        if isinstance(amount_msat, (int, float)):
            amount_sat = int(amount_msat) // _MSATS_PER_SAT
        elif isinstance(amount_direct, (int, float)):
            amount_sat = int(amount_direct)

        fees_msat = tx.get("fees_paid_msat") or tx.get("fee_msat") or tx.get("fees_msat")
        fees_direct = tx.get("fees_paid") or tx.get("fee") or tx.get("fees") or 0
        if isinstance(fees_msat, (int, float)):
            fees_sat = int(fees_msat) // _MSATS_PER_SAT
        else:
            fees_sat = int(fees_direct or 0) if isinstance(fees_direct, (int, float)) else 0

        description = str(tx.get("description") or tx.get("memo") or tx.get("note") or "")

        settled_at = tx.get("settled_at") or tx.get("paid_at") or tx.get("confirmed_at")
        created_at = tx.get("created_at") or tx.get("timestamp")
        payment_hash = str(tx.get("payment_hash") or tx.get("hash") or "")

        settled = settled_at is not None or bool(tx.get("settled") or tx.get("paid"))

        result.append({
            "type": tx_type,
            "amount_sat": amount_sat,
            "fees_sat": fees_sat,
            "description": description,
            "settled_at": int(settled_at) if isinstance(settled_at, (int, float)) else None,
            "created_at": int(created_at) if isinstance(created_at, (int, float)) else None,
            "payment_hash": payment_hash,
            "settled": settled,
        })

    # Sort newest first
    result.sort(key=lambda x: x.get("settled_at") or x.get("created_at") or 0, reverse=True)
    return result
