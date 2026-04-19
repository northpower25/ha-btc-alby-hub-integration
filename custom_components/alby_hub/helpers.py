"""Helpers for runtime access."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from homeassistant.core import HomeAssistant

from .api import AlbyHubApiClient
from .const import DOMAIN
from .coordinator import AlbyHubDataUpdateCoordinator
from .nwc import NwcConnectionInfo

if TYPE_CHECKING:
    from .text import AlbyHubTextEntity


@dataclass(slots=False)  # slots=False required to allow mutable default (text_entities dict)
class AlbyHubRuntime:
    """Runtime objects bound to one config entry."""

    coordinator: AlbyHubDataUpdateCoordinator
    api_client: AlbyHubApiClient | None
    nwc_info: NwcConnectionInfo
    text_entities: dict[str, "AlbyHubTextEntity"] = field(default_factory=dict)


def get_runtime(hass: HomeAssistant, entry_id: str) -> AlbyHubRuntime:
    """Return runtime for config entry."""
    return hass.data[DOMAIN][entry_id]
