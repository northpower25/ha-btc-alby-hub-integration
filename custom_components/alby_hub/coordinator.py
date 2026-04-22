"""Data coordinator for Alby Hub."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
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
_BLOCKCHAIN_STATS_API = "https://api.blockchain.info/stats"
_NUMERIC_BUDGET_TOTAL_MSAT_KEYS: tuple[str, ...] = (
    "total_budget_msat",
    "budget_msat",
    "limit_msat",
    "max_budget_msat",
)
_NUMERIC_BUDGET_USED_MSAT_KEYS: tuple[str, ...] = (
    "used_budget_msat",
    "used_msat",
    "spent_msat",
)
_NUMERIC_BUDGET_TOTAL_SAT_KEYS: tuple[str, ...] = (
    "total_budget_sat",
    "budget_sat",
    "limit_sat",
    "total_budget",
    "budget",
    "limit",
    "max_budget",
)
_NUMERIC_BUDGET_USED_SAT_KEYS: tuple[str, ...] = (
    "used_budget_sat",
    "used_sat",
    "spent_sat",
    "used_budget",
    "used",
    "spent",
)
_RENEWAL_KEYS: tuple[str, ...] = (
    "renewal_period",
    "renewal",
    "period",
    "budget_renewal",
    "budget_period",
)
_NETWORK_HEIGHT_KEYS: tuple[str, ...] = (
    "block_height",
    "blockheight",
    "height",
    "best_height",
    "current_block_height",
)
_LIGHTNING_ADDRESS_KEYS: tuple[str, ...] = (
    "lud16",
    "lightning_address",
    "lnaddress",
    "ln_addr",
)


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
        self._manual_lightning_address = _first_valid_lightning_address(manual_lightning_address)

    async def _async_update_data(self) -> dict[str, Any]:
        debug_calls: dict[str, dict[str, Any]] = {}
        lightning_address = _first_valid_lightning_address(
            self._manual_lightning_address,
            self._nwc_info.lud16,
        )
        data: dict[str, Any] = {
            "mode": self._mode,
            "entry_name": self._entry_name,
            "wallet_pubkey": self._nwc_info.wallet_pubkey,
            "relay": self._nwc_info.relay,
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
            "api_debug_status": "ok",
            "api_debug_details": {"updated_at": None, "errors": 0, "calls": {}},
        }

        if self._mode == MODE_EXPERT and self._api_client is not None:
            health_ok = await self._api_client.health_check()
            if health_ok:
                _record_debug_call(
                    debug_calls,
                    name="expert.health_check",
                    status="ok",
                    response={"healthy": True},
                )
            else:
                _record_debug_call(
                    debug_calls,
                    name="expert.health_check",
                    status="error",
                    error="health_check returned false",
                    response={"healthy": False},
                    log_failure=True,
                )
                data["connected"] = False
                # Keep data flow alive via NWC fallback if local expert API is
                # currently unavailable.
                await self._fetch_nwc_data(data, debug_calls)
            else:
                try:
                    info = await self._api_client.get_info()
                    _record_debug_call(
                        debug_calls,
                        name="expert.get_info",
                        status="ok",
                        response=info,
                    )
                    balance = await self._api_client.get_balance()
                    _record_debug_call(
                        debug_calls,
                        name="expert.get_balance",
                        status="ok",
                        response=balance,
                    )
                except AlbyHubApiError as err:
                    _record_debug_call(
                        debug_calls,
                        name="expert.api",
                        status="error",
                        error=str(err),
                        log_failure=True,
                    )
                    raise UpdateFailed(f"Failed to fetch expert-mode API data: {err}") from err

                data["connected"] = True
                data["version"] = info.get("version")
                data["alias"] = info.get("alias") or info.get("name")

                # Extract lightning address from local API info when not already known
                if _is_missing_lightning_address(data.get("lightning_address")):
                    api_address = _first_valid_lightning_address(
                        info.get("lightning_address"),
                        info.get("lud16"),
                        info.get("lnaddress"),
                        info.get("ln_addr"),
                    )
                    if not _is_missing_lightning_address(api_address):
                        data["lightning_address"] = str(api_address).strip()
                    elif self._manual_lightning_address:
                        data["lightning_address"] = self._manual_lightning_address

                lightning = balance.get("lightning") if isinstance(balance, dict) else None
                onchain = balance.get("onchain") if isinstance(balance, dict) else None
                data["balance_lightning"] = _read_sat_value(lightning)
                data["balance_onchain"] = _read_sat_value(onchain)

                # Fetch recent transactions in expert mode
                try:
                    txs = await self._api_client.list_transactions(limit=50)
                    data["transactions"] = _normalize_transactions(txs)
                    _record_debug_call(
                        debug_calls,
                        name="expert.list_transactions",
                        status="ok",
                        request={"limit": 50},
                        response=txs,
                    )
                except AlbyHubApiError as err:
                    _record_debug_call(
                        debug_calls,
                        name="expert.list_transactions",
                        status="error",
                        request={"limit": 50},
                        error=str(err),
                        log_failure=True,
                    )
                    _LOGGER.debug("Failed to fetch transactions (expert mode): %s", err)
        else:
            # Cloud / NWC-only mode: fetch balance and info via NWC protocol
            await self._fetch_nwc_data(data, debug_calls)

        if _is_missing_lightning_address(data.get("lightning_address")):
            data["lightning_address"] = _first_valid_lightning_address(
                self._manual_lightning_address,
                self._nwc_info.lud16,
            )

        data["bitcoin_price"] = await _fetch_bitcoin_price(
            self._session, self._price_provider, self._price_currency, debug_calls
        )
        network_stats = await _fetch_network_stats(
            self._session, self._network_provider, self._network_api_base, debug_calls
        )
        data.update({
            key: value
            for key, value in network_stats.items()
            if value is not None
        })
        _finalize_debug_payload(data, debug_calls)

        return data

    async def _fetch_nwc_data(
        self, data: dict[str, Any], debug_calls: dict[str, dict[str, Any]]
    ) -> None:
        """Fetch Lightning balance and hub info via NWC get_balance / get_info / get_budget.

        Updates *data* in-place.  All failures are silently logged at DEBUG
        level so that other sensors are not affected.
        """
        request_succeeded = False

        # get_balance → balance_lightning (NWC returns balance in millisatoshis)
        try:
            result = await async_nwc_request(self._session, self._nwc_info, "get_balance")
            request_payload = {"method": "get_balance", "params": {}}
            if result is not None and result.get("error") is None:
                request_succeeded = True
                bal_result = result.get("result") or {}
                bal_sat = _extract_nwc_balance_sat(bal_result)
                if bal_sat is not None:
                    data["balance_lightning"] = bal_sat
                onchain_sat = _extract_nwc_onchain_balance_sat(bal_result)
                if onchain_sat is not None:
                    data["balance_onchain"] = onchain_sat
                _apply_budget_from_payload(data, bal_result)
                _record_debug_call(
                    debug_calls,
                    name="nwc.get_balance",
                    status="ok",
                    request=request_payload,
                    response=result,
                )
            else:
                error_text = _extract_nwc_error(result)
                _record_debug_call(
                    debug_calls,
                    name="nwc.get_balance",
                    status="error",
                    request=request_payload,
                    response=result,
                    error=error_text,
                    log_failure=True,
                )
        except Exception as err:
            _record_debug_call(
                debug_calls,
                name="nwc.get_balance",
                status="error",
                request={"method": "get_balance", "params": {}},
                error=str(err),
                log_failure=True,
            )
            _LOGGER.debug("NWC get_balance failed: %s", err)

        # get_info → version, and lightning_address fallback if not in URI
        try:
            result = await async_nwc_request(self._session, self._nwc_info, "get_info")
            request_payload = {"method": "get_info", "params": {}}
            if result is not None and result.get("error") is None:
                request_succeeded = True
                info_result = result.get("result") or {}
                version = info_result.get("version")
                if version:
                    data["version"] = str(version)
                relay = _extract_relay(info_result)
                if relay:
                    data["relay"] = relay
                if _is_missing_lightning_address(data.get("lightning_address")):
                    address_candidate = _first_valid_lightning_address(
                        *(_extract_lightning_address_candidates(info_result)),
                    )
                    if not _is_missing_lightning_address(address_candidate):
                        data["lightning_address"] = str(address_candidate).strip()
                    elif self._manual_lightning_address:
                        data["lightning_address"] = self._manual_lightning_address
                block_height = _extract_network_height(info_result)
                if block_height is not None:
                    data["bitcoin_block_height"] = block_height
                    next_halving_height = _calculate_next_halving_height(block_height)
                    data["blocks_until_halving"] = max(next_halving_height - block_height, 0)
                _apply_budget_from_payload(data, info_result)
                _record_debug_call(
                    debug_calls,
                    name="nwc.get_info",
                    status="ok",
                    request=request_payload,
                    response=result,
                )
            else:
                error_text = _extract_nwc_error(result)
                _record_debug_call(
                    debug_calls,
                    name="nwc.get_info",
                    status="error",
                    request=request_payload,
                    response=result,
                    error=error_text,
                    log_failure=True,
                )
        except Exception as err:
            _record_debug_call(
                debug_calls,
                name="nwc.get_info",
                status="error",
                request={"method": "get_info", "params": {}},
                error=str(err),
                log_failure=True,
            )
            _LOGGER.debug("NWC get_info failed: %s", err)

        # get_budget → NWC spending limits (optional, not supported by all implementations)
        try:
            result = await async_nwc_request(self._session, self._nwc_info, "get_budget")
            request_payload = {"method": "get_budget", "params": {}}
            if result is not None and result.get("error") is None:
                request_succeeded = True
                budget_result = result.get("result") or {}
                _apply_budget_from_payload(data, budget_result)
                _record_debug_call(
                    debug_calls,
                    name="nwc.get_budget",
                    status="ok",
                    request=request_payload,
                    response=result,
                )
            else:
                error_text = _extract_nwc_error(result)
                _record_debug_call(
                    debug_calls,
                    name="nwc.get_budget",
                    status="error",
                    request=request_payload,
                    response=result,
                    error=error_text,
                    log_failure=True,
                )
        except Exception as err:
            _record_debug_call(
                debug_calls,
                name="nwc.get_budget",
                status="error",
                request={"method": "get_budget", "params": {}},
                error=str(err),
                log_failure=True,
            )
            _LOGGER.debug("NWC get_budget failed: %s", err)

        # list_transactions → recent payment history
        try:
            # Include unpaid invoices so newly created receive requests also appear in Activity.
            result = await async_nwc_request(
                self._session, self._nwc_info, "list_transactions",
                {"limit": 50, "unpaid": True},
            )
            request_payload = {"method": "list_transactions", "params": {"limit": 50, "unpaid": True}}
            if result is not None and result.get("error") is None:
                request_succeeded = True
                tx_result = result.get("result") or {}
                raw_txs = (
                    tx_result
                    if isinstance(tx_result, list)
                    else (tx_result.get("transactions") or tx_result.get("data") or [])
                )
                data["transactions"] = _normalize_transactions(raw_txs)
                _record_debug_call(
                    debug_calls,
                    name="nwc.list_transactions",
                    status="ok",
                    request=request_payload,
                    response=result,
                )
            else:
                error_text = _extract_nwc_error(result)
                _record_debug_call(
                    debug_calls,
                    name="nwc.list_transactions",
                    status="error",
                    request=request_payload,
                    response=result,
                    error=error_text,
                    log_failure=True,
                )
        except Exception as err:
            _record_debug_call(
                debug_calls,
                name="nwc.list_transactions",
                status="error",
                request={"method": "list_transactions", "params": {"limit": 50, "unpaid": True}},
                error=str(err),
                log_failure=True,
            )
            _LOGGER.debug("NWC list_transactions failed: %s", err)

        data["connected"] = request_succeeded


def _read_sat_value(value: Any) -> int | None:
    """Read satoshi-like values from known Alby API balance shapes."""
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, dict):
        for key in _BALANCE_KEYS:
            nested = value.get(key)
            if isinstance(nested, bool):
                continue
            if isinstance(nested, (int, float)):
                return int(nested)
    return None


async def _fetch_bitcoin_price(
    session: ClientSession,
    provider: str,
    currency: str,
    debug_calls: dict[str, dict[str, Any]],
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
        price = await _fetch_bitcoin_price_from_provider(
            session, candidate, currency, debug_calls
        )
        if price is not None:
            return price
    _record_debug_call(
        debug_calls,
        name="price.final",
        status="error",
        error=f"no provider returned price for {currency}",
        log_failure=True,
    )
    return None


async def _fetch_network_stats(
    session: ClientSession,
    provider: str,
    api_base: str | None,
    debug_calls: dict[str, dict[str, Any]],
) -> dict[str, int | float | None]:
    if provider == NETWORK_PROVIDER_CUSTOM_NODE and api_base:
        custom_base = api_base.rstrip("/")
        stats = await _fetch_network_stats_from_base(
            session, custom_base, "network.custom", debug_calls
        )
        if stats["bitcoin_block_height"] is not None:
            return stats
        _record_debug_call(
            debug_calls,
            name="network.custom",
            status="error",
            error=f"no block height from custom provider {custom_base}",
            log_failure=True,
        )
        _LOGGER.debug(
            "Custom network provider did not return valid data; falling back to %s",
            _DEFAULT_MEMPOOL_API,
        )

    if provider in (NETWORK_PROVIDER_MEMPOOL, NETWORK_PROVIDER_CUSTOM_NODE):
        mempool_stats = await _fetch_network_stats_from_base(
            session, _DEFAULT_MEMPOOL_API, "network.mempool", debug_calls
        )
        if mempool_stats["bitcoin_block_height"] is not None:
            return mempool_stats

    blockchain_stats = await _fetch_network_stats_from_blockchain(session, debug_calls)
    if blockchain_stats["bitcoin_block_height"] is not None:
        return blockchain_stats
    _record_debug_call(
        debug_calls,
        name="network.final",
        status="error",
        error="no network provider returned block height",
        log_failure=True,
    )
    return _empty_network_payload()


def _empty_network_payload() -> dict[str, None | float]:
    return {
        "bitcoin_block_height": None,
        "bitcoin_hashrate": None,
        "blocks_until_halving": None,
        "minutes_per_block": _MINUTES_PER_BLOCK,
    }


async def _fetch_bitcoin_price_from_provider(
    session: ClientSession,
    provider: str,
    currency: str,
    debug_calls: dict[str, dict[str, Any]],
) -> float | None:
    try:
        if provider == PRICE_PROVIDER_COINGECKO:
            data = await _safe_get_json(
                session,
                f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={currency.lower()}",
                call_name=f"price.{provider}",
                debug_calls=debug_calls,
            )
            value = data.get("bitcoin", {}).get(currency.lower()) if isinstance(data, dict) else None
            if value is None:
                _record_debug_call(
                    debug_calls,
                    name=f"price.{provider}",
                    status="error",
                    error=f"missing currency {currency}",
                    response=data,
                )
            return float(value) if value is not None else None

        if provider == PRICE_PROVIDER_COINBASE:
            data = await _safe_get_json(
                session,
                f"https://api.coinbase.com/v2/prices/BTC-{currency}/spot",
                call_name=f"price.{provider}",
                debug_calls=debug_calls,
            )
            amount = data.get("data", {}).get("amount") if isinstance(data, dict) else None
            if amount is None:
                _record_debug_call(
                    debug_calls,
                    name=f"price.{provider}",
                    status="error",
                    error=f"missing amount for {currency}",
                    response=data,
                )
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_BINANCE:
            data = await _safe_get_json(
                session,
                f"https://api.binance.com/api/v3/ticker/price?symbol=BTC{currency}",
                call_name=f"price.{provider}",
                debug_calls=debug_calls,
            )
            amount = data.get("price") if isinstance(data, dict) else None
            if amount is None:
                _record_debug_call(
                    debug_calls,
                    name=f"price.{provider}",
                    status="error",
                    error=f"missing amount for {currency}",
                    response=data,
                )
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_BLOCKCHAIN:
            data = await _safe_get_json(
                session,
                "https://blockchain.info/ticker",
                call_name=f"price.{provider}",
                debug_calls=debug_calls,
            )
            amount = data.get(currency, {}).get("last") if isinstance(data, dict) else None
            if amount is None:
                _record_debug_call(
                    debug_calls,
                    name=f"price.{provider}",
                    status="error",
                    error=f"missing currency {currency}",
                    response=data,
                )
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_COINDESK:
            _record_debug_call(
                debug_calls,
                name=f"price.{provider}",
                status="error",
                error="provider deprecated",
            )
            _LOGGER.debug("CoinDesk v1 API is no longer available; trying fallback provider")
            return None

        if provider == PRICE_PROVIDER_MEMPOOL:
            data = await _safe_get_json(
                session,
                f"{_DEFAULT_MEMPOOL_API}/api/v1/prices",
                call_name=f"price.{provider}",
                debug_calls=debug_calls,
            )
            amount = data.get(currency) if isinstance(data, dict) else None
            if amount is None:
                _LOGGER.debug(
                    "Mempool price API did not return data for currency %s; available keys: %s",
                    currency,
                    list(data.keys()) if isinstance(data, dict) else data,
                )
                _record_debug_call(
                    debug_calls,
                    name=f"price.{provider}",
                    status="error",
                    error=f"missing currency {currency}",
                    response=data,
                )
            return float(amount) if amount is not None else None

        if provider in (PRICE_PROVIDER_BITCOIN_DE, PRICE_PROVIDER_BITQUERY):
            _record_debug_call(
                debug_calls,
                name=f"price.{provider}",
                status="error",
                error="provider not implemented",
            )
            _LOGGER.debug("Price provider %s is not implemented; trying fallback provider", provider)
            return None
    except (TypeError, ValueError) as err:
        _record_debug_call(
            debug_calls,
            name=f"price.{provider}",
            status="error",
            error=str(err),
            log_failure=True,
        )
        return None

    return None


async def _fetch_network_stats_from_base(
    session: ClientSession,
    base_url: str,
    source_name: str,
    debug_calls: dict[str, dict[str, Any]],
) -> dict[str, int | float | None]:
    height_data = await _safe_get_json(
        session,
        f"{base_url}/api/blocks/tip/height",
        call_name=f"{source_name}.height",
        debug_calls=debug_calls,
    )
    hashrate_data = await _safe_get_json(
        session,
        f"{base_url}/api/v1/mining/hashrate/3d",
        call_name=f"{source_name}.hashrate",
        debug_calls=debug_calls,
    )

    if not isinstance(height_data, int):
        _record_debug_call(
            debug_calls,
            name=source_name,
            status="error",
            error=f"invalid block height response from {base_url}",
            response=height_data,
        )
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


async def _fetch_network_stats_from_blockchain(
    session: ClientSession,
    debug_calls: dict[str, dict[str, Any]],
) -> dict[str, int | float | None]:
    data = await _safe_get_json(
        session,
        _BLOCKCHAIN_STATS_API,
        call_name="network.blockchain_com",
        debug_calls=debug_calls,
    )
    if not isinstance(data, dict):
        _record_debug_call(
            debug_calls,
            name="network.blockchain_com",
            status="error",
            error="invalid response payload",
            response=data,
        )
        return _empty_network_payload()

    block_height = data.get("n_blocks_total")
    if not isinstance(block_height, int):
        _record_debug_call(
            debug_calls,
            name="network.blockchain_com",
            status="error",
            error="missing n_blocks_total",
            response=data,
        )
        return _empty_network_payload()

    raw_hashrate = data.get("hash_rate")
    hashrate = None
    if isinstance(raw_hashrate, (int, float)):
        # Blockchain.info reports TH/s; 1 EH/s = 1,000,000 TH/s.
        hashrate = round(float(raw_hashrate) / 1_000_000, 2)

    minutes_per_block = data.get("minutes_between_blocks")
    if not isinstance(minutes_per_block, (int, float)) or float(minutes_per_block) <= 0:
        minutes_per_block = _MINUTES_PER_BLOCK

    next_halving_height = _calculate_next_halving_height(block_height)
    blocks_until_halving = max(next_halving_height - block_height, 0)

    return {
        "bitcoin_block_height": block_height,
        "bitcoin_hashrate": hashrate,
        "blocks_until_halving": blocks_until_halving,
        "minutes_per_block": float(minutes_per_block),
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


def _extract_nwc_onchain_balance_sat(balance_result: Any) -> int | None:
    if not isinstance(balance_result, dict):
        return None

    sat_keys = (
        "onchain_balance_sat",
        "onchain_sat",
        "onchain",
        "balance_onchain",
        "confirmed_balance",
        "onchain_confirmed",
    )
    for key in sat_keys:
        value = balance_result.get(key)
        if isinstance(value, dict):
            nested = _read_sat_value(value)
            if nested is not None:
                return nested
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value)

    msat_keys = (
        "onchain_balance_msat",
        "onchain_msat",
        "balance_onchain_msat",
    )
    for key in msat_keys:
        value = balance_result.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, (int, float)):
            return int(value) // _MSATS_PER_SAT

    return None


def _extract_lightning_address_candidates(payload: dict[str, Any]) -> tuple[Any, ...]:
    candidates: list[Any] = []
    for key in _LIGHTNING_ADDRESS_KEYS:
        candidates.append(payload.get(key))
    profile = payload.get("profile")
    if isinstance(profile, dict):
        for key in _LIGHTNING_ADDRESS_KEYS:
            candidates.append(profile.get(key))
    wallet = payload.get("wallet")
    if isinstance(wallet, dict):
        for key in _LIGHTNING_ADDRESS_KEYS:
            candidates.append(wallet.get(key))
    return tuple(candidates)


def _extract_relay(payload: dict[str, Any]) -> str | None:
    relay = payload.get("relay")
    if isinstance(relay, str) and relay.strip():
        return relay.strip()

    relays = payload.get("relays")
    if isinstance(relays, list):
        for candidate in relays:
            if isinstance(candidate, str) and candidate.strip():
                return candidate.strip()

    return None


def _extract_network_height(payload: dict[str, Any]) -> int | None:
    height = _find_first_numeric(payload, _NETWORK_HEIGHT_KEYS)
    return height if isinstance(height, int) and height > 0 else None


def _apply_budget_from_payload(data: dict[str, Any], payload: Any) -> None:
    if not isinstance(payload, dict):
        return

    used_sat = _find_first_numeric(payload, _NUMERIC_BUDGET_USED_MSAT_KEYS)
    if isinstance(used_sat, int):
        used_sat //= _MSATS_PER_SAT
    else:
        used_sat = _find_first_numeric(payload, _NUMERIC_BUDGET_USED_SAT_KEYS)

    total_sat = _find_first_numeric(payload, _NUMERIC_BUDGET_TOTAL_MSAT_KEYS)
    if isinstance(total_sat, int):
        total_sat //= _MSATS_PER_SAT
    else:
        total_sat = _find_first_numeric(payload, _NUMERIC_BUDGET_TOTAL_SAT_KEYS)

    renewal = _find_first_text(payload, _RENEWAL_KEYS)

    if isinstance(used_sat, int) and used_sat >= 0:
        data["nwc_budget_used"] = used_sat
    if isinstance(total_sat, int) and total_sat >= 0:
        data["nwc_budget_total"] = total_sat
    if data.get("nwc_budget_total") is not None and data.get("nwc_budget_used") is not None:
        data["nwc_budget_remaining"] = max(
            0, int(data["nwc_budget_total"]) - int(data["nwc_budget_used"])
        )
    if renewal:
        data["nwc_budget_renewal"] = renewal


def _find_first_numeric(payload: dict[str, Any], keys: tuple[str, ...]) -> int | None:
    for container in _collect_dict_candidates(payload):
        for key in keys:
            raw = container.get(key)
            if isinstance(raw, bool):
                continue
            if isinstance(raw, (int, float)):
                return int(raw)
            if isinstance(raw, str):
                stripped = raw.strip()
                if not stripped:
                    continue
                try:
                    return int(float(stripped))
                except ValueError:
                    continue
    return None


def _find_first_text(payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
    for container in _collect_dict_candidates(payload):
        for key in keys:
            raw = container.get(key)
            if isinstance(raw, str) and raw.strip():
                return raw.strip()
    return None


def _collect_dict_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = [payload]
    nested_keys = (
        "result",
        "budget",
        "limits",
        "limit",
        "spending",
        "wallet",
        "profile",
        "info",
    )
    for key in nested_keys:
        nested = payload.get(key)
        if isinstance(nested, dict):
            candidates.append(nested)
    return candidates


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


async def _safe_get_json(
    session: ClientSession,
    url: str,
    *,
    call_name: str | None = None,
    debug_calls: dict[str, dict[str, Any]] | None = None,
) -> Any:
    headers = {
        "Accept": "application/json,text/plain,*/*",
        "User-Agent": "HomeAssistant AlbyHub Integration",
    }
    try:
        result: Any = None
        async with session.get(
            url,
            timeout=ClientTimeout(total=_API_REQUEST_TIMEOUT_SECONDS),
            headers=headers,
        ) as response:
            if response.status >= 400:
                if call_name and debug_calls is not None:
                    _record_debug_call(
                        debug_calls,
                        name=call_name,
                        status="error",
                        request={"url": url},
                        error=f"http_status_{response.status}",
                        log_failure=True,
                    )
                _LOGGER.debug("HTTP %s fetching %s", response.status, url)
                return None
            content_type = response.headers.get("Content-Type", "").lower()
            if "json" in content_type:
                result = await response.json(content_type=None)
            else:
                raw_text = (await response.text()).strip()
                if raw_text:
                    try:
                        result = int(raw_text)
                    except ValueError:
                        try:
                            result = float(raw_text)
                        except ValueError:
                            result = raw_text
                else:
                    try:
                        result = await response.json(content_type=None)
                    except ValueError:
                        result = None
        if call_name and debug_calls is not None:
            _record_debug_call(
                debug_calls,
                name=call_name,
                status="ok" if result is not None else "error",
                request={"url": url},
                response=result if result is not None else "empty",
                error=None if result is not None else "empty response",
            )
        return result
    except TimeoutError:
        if call_name and debug_calls is not None:
            _record_debug_call(
                debug_calls,
                name=call_name,
                status="error",
                request={"url": url},
                error="timeout",
                log_failure=True,
            )
        _LOGGER.debug("Timeout fetching %s", url)
        return None
    except (ClientError, ValueError) as err:
        if call_name and debug_calls is not None:
            _record_debug_call(
                debug_calls,
                name=call_name,
                status="error",
                request={"url": url},
                error=str(err),
                log_failure=True,
            )
        _LOGGER.debug("Error fetching %s: %s", url, err)
        return None


def _extract_nwc_error(result: Any) -> str:
    if result is None:
        return "no response"
    if isinstance(result, dict):
        error = result.get("error")
        if isinstance(error, dict):
            message = error.get("message") or error.get("code") or str(error)
            return str(message)
        if error is not None:
            return str(error)
    return "unknown error"


def _record_debug_call(
    debug_calls: dict[str, dict[str, Any]],
    *,
    name: str,
    status: str,
    request: Any = None,
    response: Any = None,
    error: str | None = None,
    log_failure: bool = False,
) -> None:
    entry: dict[str, Any] = {"status": status}
    if request is not None:
        entry["request"] = _to_debug_payload(request)
    if response is not None:
        entry["response"] = _to_debug_payload(response)
    if error:
        entry["error"] = str(error)
    debug_calls[name] = entry

    if status != "ok" and (log_failure or error):
        _LOGGER.warning("API debug [%s] failed: %s", name, error or "no data returned")


def _to_debug_payload(value: Any, max_length: int = 1200) -> Any:
    if isinstance(value, (dict, list, tuple, int, float, bool)) or value is None:
        rendered = repr(value)
    else:
        rendered = str(value)
    if len(rendered) > max_length:
        rendered = f"{rendered[:max_length]}... [truncated]"
    return rendered


def _finalize_debug_payload(
    data: dict[str, Any], debug_calls: dict[str, dict[str, Any]]
) -> None:
    errors = sum(1 for details in debug_calls.values() if details.get("status") != "ok")
    data["api_debug_status"] = "ok" if errors == 0 else f"errors:{errors}"
    data["api_debug_details"] = {
        "updated_at": datetime.now(UTC).isoformat(),
        "errors": errors,
        "calls": debug_calls,
    }


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
