"""Data coordinator for Alby Hub."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import AlbyHubApiClient, AlbyHubApiError
from .const import MODE_EXPERT
from .nwc import NwcConnectionInfo

_LOGGER = logging.getLogger(__name__)
_BALANCE_KEYS: tuple[str, ...] = ("balance", "sat", "sats", "total")


class AlbyHubDataUpdateCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Fetch Alby Hub status for entities."""

    def __init__(
        self,
        hass: HomeAssistant,
        *,
        mode: str,
        nwc_info: NwcConnectionInfo,
        api_client: AlbyHubApiClient | None,
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

    async def _async_update_data(self) -> dict[str, Any]:
        data: dict[str, Any] = {
            "mode": self._mode,
            "wallet_pubkey": self._nwc_info.wallet_pubkey,
            "relay": self._nwc_info.relay,
            "lightning_address": self._nwc_info.lud16,
            "connected": self._mode != MODE_EXPERT,
            "balance_lightning": None,
            "balance_onchain": None,
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
