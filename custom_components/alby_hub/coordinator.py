"""Data coordinator for Alby Hub."""

from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta
from typing import Any

from aiohttp import ClientError, ClientSession
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

_LOGGER = logging.getLogger(__name__)
_BALANCE_KEYS: tuple[str, ...] = ("balance", "sat", "sats", "total")
_HALVING_INTERVAL_BLOCKS = 210000
_MINUTES_PER_BLOCK = 10
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

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "mode": self._mode,
            "wallet_pubkey": self._nwc_info.wallet_pubkey,
            "relay": self._nwc_info.relay,
            "lightning_address": self._nwc_info.lud16,
            "connected": self._mode != MODE_EXPERT,
            "balance_lightning": None,
            "balance_onchain": None,
            "bitcoin_block_height": None,
            "bitcoin_hashrate": None,
            "bitcoin_price": None,
            "blocks_until_halving": None,
            "next_halving_eta": None,
            "price_currency": self._price_currency,
            "version": None,
            "alias": None,
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

        data["bitcoin_price"] = await _fetch_bitcoin_price(
            self._session, self._price_provider, self._price_currency
        )
        network_stats = await _fetch_network_stats(
            self._session, self._network_provider, self._network_api_base
        )
        data.update(network_stats)

        return data


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
    try:
        if provider == PRICE_PROVIDER_COINGECKO:
            data = await _safe_get_json(
                session,
                f"https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies={currency.lower()}",
            )
            value = data.get("bitcoin", {}).get(currency.lower())
            return float(value) if value is not None else None

        if provider == PRICE_PROVIDER_COINBASE:
            data = await _safe_get_json(
                session, f"https://api.coinbase.com/v2/prices/spot?currency={currency}"
            )
            amount = data.get("data", {}).get("amount")
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_BINANCE:
            data = await _safe_get_json(
                session, f"https://api.binance.com/api/v3/ticker/price?symbol=BTC{currency}"
            )
            amount = data.get("price")
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_BLOCKCHAIN:
            data = await _safe_get_json(session, "https://blockchain.info/ticker")
            amount = data.get(currency, {}).get("last")
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_COINDESK:
            data = await _safe_get_json(
                session, f"https://api.coindesk.com/v1/bpi/currentprice/{currency}.json"
            )
            amount = data.get("bpi", {}).get(currency, {}).get("rate_float")
            return float(amount) if amount is not None else None

        if provider == PRICE_PROVIDER_MEMPOOL:
            data = await _safe_get_json(session, f"{_DEFAULT_MEMPOOL_API}/api/v1/prices")
            amount = data.get(currency)
            return float(amount) if amount is not None else None

        if provider in (PRICE_PROVIDER_BITCOIN_DE, PRICE_PROVIDER_BITQUERY):
            return None
    except (TypeError, ValueError):
        return None

    return None


async def _fetch_network_stats(
    session: ClientSession, provider: str, api_base: str | None
) -> dict[str, int | float | datetime | None]:
    if provider not in (NETWORK_PROVIDER_MEMPOOL, NETWORK_PROVIDER_CUSTOM_NODE):
        return _empty_network_payload()

    base_url = _DEFAULT_MEMPOOL_API
    if provider == NETWORK_PROVIDER_CUSTOM_NODE and api_base:
        base_url = api_base.rstrip("/")

    height_data = await _safe_get_json(session, f"{base_url}/api/blocks/tip/height")
    hashrate_data = await _safe_get_json(session, f"{base_url}/api/v1/mining/hashrate/3d")

    if not isinstance(height_data, int):
        return _empty_network_payload()

    hashrate = None
    minutes_per_block = _MINUTES_PER_BLOCK
    if isinstance(hashrate_data, dict):
        current = hashrate_data.get("currentHashrate")
        if isinstance(current, (int, float)):
            hashrate = round(float(current) / 1_000_000_000_000_000_000, 2)
        avg_block_time_seconds = hashrate_data.get("avgBlockTime")
        if isinstance(avg_block_time_seconds, (int, float)) and avg_block_time_seconds > 0:
            minutes_per_block = float(avg_block_time_seconds) / 60

    if height_data % _HALVING_INTERVAL_BLOCKS == 0:
        next_halving_height = height_data
    else:
        next_halving_height = ((height_data // _HALVING_INTERVAL_BLOCKS) + 1) * _HALVING_INTERVAL_BLOCKS
    blocks_until_halving = max(next_halving_height - height_data, 0)
    next_halving_eta = datetime.now(UTC) + timedelta(
        minutes=blocks_until_halving * minutes_per_block
    )

    return {
        "bitcoin_block_height": height_data,
        "bitcoin_hashrate": hashrate,
        "blocks_until_halving": blocks_until_halving,
        "next_halving_eta": next_halving_eta,
    }


def _empty_network_payload() -> dict[str, None]:
    return {
        "bitcoin_block_height": None,
        "bitcoin_hashrate": None,
        "blocks_until_halving": None,
        "next_halving_eta": None,
    }


async def _safe_get_json(session: ClientSession, url: str) -> Any:
    try:
        async with session.get(url, timeout=5) as response:
            if response.status >= 400:
                return None
            return await response.json(content_type=None)
    except (TimeoutError, ClientError, ValueError):
        return None
