"""Address book management for the Alby Hub integration.

Stores contact entries persistently via HA's storage helper.

Each contact entry carries:
    id              : unique str (UUID)
    last_name       : family name
    first_name      : given name
    nostr_alias     : human-readable Nostr handle / alias
    nostr_pubkey    : Nostr public key (npub or 64-char hex)
    lightning_address : e.g. user@domain.com
    bitcoin_address : on-chain Bitcoin address (bc1…, 1…, 3…)
    notes           : free-text notes
    tags            : list of tag strings for grouping
    created_at      : ISO datetime string
    updated_at      : ISO datetime string
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.storage import Store

_LOGGER = logging.getLogger(__name__)

STORAGE_KEY_ADDRESS_BOOK = "alby_hub_address_book"
STORAGE_VERSION_ADDRESS_BOOK = 1


def _now_iso() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


class AddressBook:
    """Manages address book contacts for one HA instance."""

    def __init__(self, hass: HomeAssistant) -> None:
        self._hass = hass
        self._store: Store = Store(
            hass,
            STORAGE_VERSION_ADDRESS_BOOK,
            STORAGE_KEY_ADDRESS_BOOK,
        )
        self._contacts: list[dict[str, Any]] = []

    # ── lifecycle ──────────────────────────────────────────────────────────────

    async def async_load(self) -> None:
        """Load contacts from persistent storage."""
        data = await self._store.async_load() or {}
        self._contacts = data.get("contacts", [])
        _LOGGER.debug("Loaded %d address book contact(s)", len(self._contacts))

    # ── public CRUD API ────────────────────────────────────────────────────────

    async def async_create(self, params: dict[str, Any]) -> dict[str, Any]:
        """Create and persist a new contact. Returns the created contact."""
        now = _now_iso()
        contact: dict[str, Any] = {
            "id": str(uuid.uuid4()),
            "last_name": str(params.get("last_name") or "").strip(),
            "first_name": str(params.get("first_name") or "").strip(),
            "nostr_alias": str(params.get("nostr_alias") or "").strip(),
            "nostr_pubkey": str(params.get("nostr_pubkey") or "").strip(),
            "lightning_address": str(params.get("lightning_address") or "").strip(),
            "bitcoin_address": str(params.get("bitcoin_address") or "").strip(),
            "notes": str(params.get("notes") or "").strip(),
            "tags": [str(t).strip() for t in (params.get("tags") or []) if str(t).strip()],
            "created_at": now,
            "updated_at": now,
        }
        self._contacts.append(contact)
        await self._save()
        _LOGGER.info(
            "Created address book contact '%s %s'",
            contact["first_name"],
            contact["last_name"],
        )
        return dict(contact)

    def list_contacts(self) -> list[dict[str, Any]]:
        """Return all contacts as safe copies, sorted by last_name, first_name."""
        return sorted(
            [dict(c) for c in self._contacts],
            key=lambda c: (c.get("last_name", "").lower(), c.get("first_name", "").lower()),
        )

    def get_contact(self, contact_id: str) -> dict[str, Any] | None:
        """Return a single contact by id, or None if not found."""
        for c in self._contacts:
            if c["id"] == contact_id:
                return dict(c)
        return None

    async def async_update(self, contact_id: str, params: dict[str, Any]) -> dict[str, Any] | None:
        """Update fields of an existing contact. Returns updated contact or None."""
        for i, c in enumerate(self._contacts):
            if c["id"] != contact_id:
                continue
            updatable = {
                "last_name", "first_name", "nostr_alias", "nostr_pubkey",
                "lightning_address", "bitcoin_address", "notes", "tags",
            }
            updated = dict(c)
            for key in updatable:
                if key not in params:
                    continue
                if key == "tags":
                    updated[key] = [str(t).strip() for t in (params[key] or []) if str(t).strip()]
                else:
                    updated[key] = str(params[key] or "").strip()
            updated["updated_at"] = _now_iso()
            self._contacts[i] = updated
            await self._save()
            _LOGGER.info(
                "Updated address book contact '%s %s'",
                updated["first_name"],
                updated["last_name"],
            )
            return dict(updated)
        return None

    async def async_delete(self, contact_id: str) -> bool:
        """Delete a contact by id. Returns True if found and removed."""
        before = len(self._contacts)
        self._contacts = [c for c in self._contacts if c["id"] != contact_id]
        if len(self._contacts) == before:
            return False
        await self._save()
        return True

    # ── private helpers ────────────────────────────────────────────────────────

    async def _save(self) -> None:
        await self._store.async_save({"contacts": self._contacts})


# ── Module-level singleton helpers (mirrors recurring_payments pattern) ────────

_ADDRESS_BOOK_KEY = "alby_hub_address_book_instance"


async def async_setup_address_book(hass: HomeAssistant) -> None:
    """Create and load the address book singleton. Idempotent."""
    if hass.data.get(_ADDRESS_BOOK_KEY) is not None:
        return
    book = AddressBook(hass)
    await book.async_load()
    hass.data[_ADDRESS_BOOK_KEY] = book


def get_address_book(hass: HomeAssistant) -> AddressBook:
    """Return the address book singleton (must call async_setup_address_book first)."""
    book = hass.data.get(_ADDRESS_BOOK_KEY)
    if book is None:
        raise RuntimeError("Address book not initialised – call async_setup_address_book first.")
    return book
