"""Helpers for runtime access."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.core import HomeAssistant

from .api import AlbyHubApiClient
from .const import DOMAIN
from .coordinator import AlbyHubDataUpdateCoordinator
from .nwc import NwcConnectionInfo


@dataclass(slots=True)
class AlbyHubRuntime:
    """Runtime objects bound to one config entry."""

    coordinator: AlbyHubDataUpdateCoordinator
    api_client: AlbyHubApiClient | None
    nwc_info: NwcConnectionInfo


def get_runtime(hass: HomeAssistant, entry_id: str) -> AlbyHubRuntime:
    """Return runtime for config entry."""
    return hass.data[DOMAIN][entry_id]
