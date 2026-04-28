"""Select platform for Alby Hub – invoice amount unit and address book contact selection."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .address_book import get_address_book
from .const import (
    SELECT_KEY_INVOICE_AMOUNT_UNIT,
    SELECT_KEY_LIGHTNING_CONTACT,
    SELECT_KEY_NOSTR_CONTACT,
)
from .entity import AlbyHubCoordinatorEntity
from .helpers import get_runtime

_LOGGER = logging.getLogger(__name__)
_DEFAULT_UNIT = "SAT"
_NO_CONTACTS_OPTION = "— no contacts —"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up invoice amount unit and contact select entities."""
    runtime = get_runtime(hass, entry.entry_id)
    unit_entity = AlbyHubInvoiceAmountUnitSelect(runtime.coordinator, entry.entry_id)
    lightning_entity = AlbyHubLightningContactSelect(hass, runtime.coordinator, entry.entry_id)
    nostr_entity = AlbyHubNostrContactSelect(hass, runtime.coordinator, entry.entry_id)
    entities: list[SelectEntity] = [unit_entity, lightning_entity, nostr_entity]
    async_add_entities(entities)
    runtime.select_entities = {e.entity_description.key: e for e in entities}


class AlbyHubInvoiceAmountUnitSelect(AlbyHubCoordinatorEntity, RestoreEntity, SelectEntity):
    """Select entity for choosing the unit of the invoice amount (SAT / BTC / Fiat)."""

    entity_description = SelectEntityDescription(
        key=SELECT_KEY_INVOICE_AMOUNT_UNIT,
        translation_key=SELECT_KEY_INVOICE_AMOUNT_UNIT,
        icon="mdi:scale-balance",
    )

    def __init__(self, coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_{SELECT_KEY_INVOICE_AMOUNT_UNIT}"
        self._attr_current_option: str = _DEFAULT_UNIT

    @property
    def options(self) -> list[str]:
        """Return selectable units: SAT, BTC, and the configured fiat currency."""
        base: list[str] = ["SAT", "BTC"]
        fiat = self.coordinator.data.get("price_currency")
        if fiat and fiat not in base:
            base.append(fiat)
        return base

    @property
    def current_option(self) -> str | None:
        """Return the currently selected unit."""
        # If stored option is no longer valid (e.g. currency changed), fall back to SAT
        if self._attr_current_option not in self.options:
            return "SAT"
        return self._attr_current_option

    async def async_added_to_hass(self) -> None:
        """Restore previously selected unit."""
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) is not None and last.state:
            self._attr_current_option = last.state

    async def async_select_option(self, option: str) -> None:
        """Handle user selecting a unit."""
        self._attr_current_option = option
        self.async_write_ha_state()


def _format_lightning_option(contact: dict) -> str:
    """Format a contact as a Lightning address option string.

    Format: "Firstname Lastname <lightning@address>" or just "lightning@address".
    The address is always extractable from the angle-bracket notation.
    """
    address = contact.get("lightning_address", "").strip()
    if not address:
        return ""
    parts = [
        contact.get("first_name", "").strip(),
        contact.get("last_name", "").strip(),
    ]
    name = " ".join(p for p in parts if p)
    if name:
        return f"{name} <{address}>"
    return address


def _format_nostr_option(contact: dict) -> str:
    """Format a contact as a Nostr contact option string.

    Format: "Firstname Lastname <npub…>" or "alias <npub…>" or just "npub…".
    """
    pubkey = contact.get("nostr_pubkey", "").strip()
    if not pubkey:
        return ""
    alias = contact.get("nostr_alias", "").strip()
    parts = [
        contact.get("first_name", "").strip(),
        contact.get("last_name", "").strip(),
    ]
    name = " ".join(p for p in parts if p) or alias
    if name:
        return f"{name} <{pubkey}>"
    return pubkey


def extract_address_from_option(option: str) -> str:
    """Extract the raw address/pubkey from an option string.

    Handles both plain addresses and "Name <address>" format.
    Returns the input unchanged if it does not match the angle-bracket pattern.
    """
    option = option.strip()
    if option.endswith(">") and "<" in option:
        start = option.rfind("<")
        return option[start + 1 : -1].strip()
    return option


class _AlbyHubContactSelectBase(AlbyHubCoordinatorEntity, RestoreEntity, SelectEntity):
    """Base class for address book contact select entities."""

    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str) -> None:
        super().__init__(coordinator, entry_id)
        self._hass = hass
        self._attr_current_option: str | None = None
        self._options_cache: list[str] = []

    # Subclasses must implement:
    def _build_options(self) -> list[str]:
        raise NotImplementedError

    def _on_address_book_changed(self) -> None:
        """Called by the address book listener when contacts change."""
        new_options = self._build_options()
        self._options_cache = new_options
        # If currently selected option no longer exists, reset
        if self._attr_current_option not in new_options:
            self._attr_current_option = new_options[0] if new_options else None
        if self.hass is not None:
            self.async_write_ha_state()

    async def async_added_to_hass(self) -> None:
        """Register address book listener and restore state."""
        await super().async_added_to_hass()
        # Build initial options
        self._options_cache = self._build_options()
        # Register listener for future changes
        try:
            book = get_address_book(self._hass)
            book.register_listener(self._on_address_book_changed)
            self.async_on_remove(lambda: book.unregister_listener(self._on_address_book_changed))
        except RuntimeError:
            _LOGGER.debug("Address book not yet initialised; contact select will refresh on first use")
        # Restore previous selection
        if (last := await self.async_get_last_state()) is not None and last.state:
            if last.state in self._options_cache:
                self._attr_current_option = last.state

    @property
    def options(self) -> list[str]:
        """Return the current list of selectable options."""
        opts = self._options_cache or self._build_options()
        if not opts:
            return [_NO_CONTACTS_OPTION]
        return opts

    @property
    def current_option(self) -> str | None:
        """Return the currently selected option."""
        if self._attr_current_option in self.options:
            return self._attr_current_option
        opts = self.options
        return opts[0] if opts else None

    async def async_select_option(self, option: str) -> None:
        """Handle the user selecting an option."""
        self._attr_current_option = option
        self.async_write_ha_state()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Expose the raw extracted address as an attribute for easy automation use."""
        current = self.current_option
        if current and current != _NO_CONTACTS_OPTION:
            return {"address": extract_address_from_option(current)}
        return {"address": ""}


class AlbyHubLightningContactSelect(_AlbyHubContactSelectBase):
    """Select entity listing address book contacts that have a Lightning address.

    The entity state holds the currently selected option in the format
    ``"Firstname Lastname <lightning@address>"`` (or just the address when no
    name is stored).  The raw Lightning address is also exposed via the
    ``address`` state attribute for easy use in templates and service calls.
    """

    entity_description = SelectEntityDescription(
        key=SELECT_KEY_LIGHTNING_CONTACT,
        translation_key=SELECT_KEY_LIGHTNING_CONTACT,
        icon="mdi:lightning-bolt",
    )

    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str) -> None:
        super().__init__(hass, coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_{SELECT_KEY_LIGHTNING_CONTACT}"

    def _build_options(self) -> list[str]:
        try:
            book = get_address_book(self._hass)
        except RuntimeError:
            return []
        return [
            opt
            for contact in book.list_contacts()
            if (opt := _format_lightning_option(contact))
        ]


class AlbyHubNostrContactSelect(_AlbyHubContactSelectBase):
    """Select entity listing address book contacts that have a Nostr public key.

    The entity state holds the currently selected option in the format
    ``"Firstname Lastname <npub…>"`` (or alias / raw pubkey when no name is
    stored).  The raw pubkey is also exposed via the ``address`` state
    attribute for easy use in templates and service calls.
    """

    entity_description = SelectEntityDescription(
        key=SELECT_KEY_NOSTR_CONTACT,
        translation_key=SELECT_KEY_NOSTR_CONTACT,
        icon="mdi:account-key",
    )

    def __init__(self, hass: HomeAssistant, coordinator, entry_id: str) -> None:
        super().__init__(hass, coordinator, entry_id)
        self._attr_unique_id = f"{entry_id}_{SELECT_KEY_NOSTR_CONTACT}"

    def _build_options(self) -> list[str]:
        try:
            book = get_address_book(self._hass)
        except RuntimeError:
            return []
        return [
            opt
            for contact in book.list_contacts()
            if (opt := _format_nostr_option(contact))
        ]
