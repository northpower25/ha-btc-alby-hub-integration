"""Nostr bot manager and webhook view."""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
from typing import Any

from aiohttp.web import Request, Response, json_response
from homeassistant.components.http import HomeAssistantView
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import DOMAIN
from .nostr_client import async_send_nip44_dm, npub_from_nsec

_LOGGER = logging.getLogger(__name__)
_MAX_MESSAGES = 250


@dataclass(slots=True)
class NostrMessage:
    """One bot chat message entry."""

    ts: str
    direction: str
    sender: str
    recipient: str
    message: str
    source: str
    status: str


class AlbyHubNostrBotManager:
    """Per-entry Nostr bot state."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry_id: str,
        relay_url: str,
        bot_nsec: str,
        allowed_npubs: str,
        webhook_secret: str,
    ) -> None:
        self.hass = hass
        self.entry_id = entry_id
        self.relay_url = (relay_url or "").strip()
        self.bot_nsec = (bot_nsec or "").strip()
        self.allowed_npubs_raw = allowed_npubs or ""
        self.webhook_secret = webhook_secret
        self._messages: deque[NostrMessage] = deque(maxlen=_MAX_MESSAGES)
        self._bot_npub = ""
        self._allowed_npubs: set[str] = set()
        self._reload_config(relay_url, bot_nsec, allowed_npubs, webhook_secret)

    @property
    def bot_npub(self) -> str:
        return self._bot_npub

    @property
    def webhook_url(self) -> str:
        return f"/api/alby_hub/nostr_webhook/{self.entry_id}"

    def _reload_config(
        self,
        relay_url: str,
        bot_nsec: str,
        allowed_npubs: str,
        webhook_secret: str,
    ) -> None:
        self.relay_url = (relay_url or "").strip()
        self.bot_nsec = (bot_nsec or "").strip()
        self.allowed_npubs_raw = allowed_npubs or ""
        self.webhook_secret = (webhook_secret or "").strip()
        self._allowed_npubs = _parse_allowed_npubs(self.allowed_npubs_raw)
        try:
            self._bot_npub = npub_from_nsec(self.bot_nsec) if self.bot_nsec else ""
        except ValueError:
            self._bot_npub = ""

    def update_from_data(self, data: dict[str, Any]) -> None:
        self._reload_config(
            relay_url=str(data.get("nostr_relay", "")),
            bot_nsec=str(data.get("nostr_bot_nsec", "")),
            allowed_npubs=str(data.get("nostr_allowed_npubs", "")),
            webhook_secret=str(data.get("nostr_webhook_secret", "")),
        )

    def is_allowed_npub(self, npub: str) -> bool:
        normalized = (npub or "").strip().lower()
        return bool(normalized and normalized in self._allowed_npubs)

    def add_message(
        self,
        direction: str,
        sender: str,
        recipient: str,
        message: str,
        source: str,
        status: str,
    ) -> None:
        self._messages.appendleft(
            NostrMessage(
                ts=datetime.now(UTC).isoformat(),
                direction=direction,
                sender=(sender or "").strip(),
                recipient=(recipient or "").strip(),
                message=(message or "").strip(),
                source=source,
                status=status,
            )
        )

    def list_messages(self, limit: int = 100) -> list[dict[str, Any]]:
        return [m.__dict__ for m in list(self._messages)[: max(1, min(limit, _MAX_MESSAGES))]]

    async def async_send_bot_message(self, target_npub: str, message: str) -> str:
        if not self.relay_url:
            raise ValueError("nostr_relay_missing")
        if not self.bot_nsec:
            raise ValueError("nostr_bot_nsec_missing")
        if not self.is_allowed_npub(target_npub):
            raise ValueError("nostr_target_not_allowed")
        event_id = await async_send_nip44_dm(
            async_get_clientsession(self.hass),
            self.relay_url,
            self.bot_nsec,
            target_npub,
            message,
        )
        self.add_message(
            direction="outgoing",
            sender=self._bot_npub,
            recipient=target_npub,
            message=message,
            source="bot",
            status="sent",
        )
        return event_id

    async def async_send_test_message(self, test_nsec: str, message: str) -> str:
        if not self.relay_url:
            raise ValueError("nostr_relay_missing")
        if not self._bot_npub:
            raise ValueError("nostr_bot_npub_unavailable")
        event_id = await async_send_nip44_dm(
            async_get_clientsession(self.hass),
            self.relay_url,
            test_nsec,
            self._bot_npub,
            message,
        )
        sender = "custom_nsec"
        try:
            sender = npub_from_nsec(test_nsec)
        except ValueError:
            sender = "custom_nsec"
        self.add_message(
            direction="test_outgoing",
            sender=sender,
            recipient=self._bot_npub,
            message=message,
            source="test",
            status="sent",
        )
        return event_id

    async def async_handle_webhook_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        sender_npub = str(payload.get("sender_npub") or payload.get("user") or "").strip()
        command = str(payload.get("command") or "").strip()
        message = str(payload.get("message") or command or "").strip()
        if not sender_npub:
            raise ValueError("missing_sender_npub")
        if not self.is_allowed_npub(sender_npub):
            raise PermissionError("sender_not_whitelisted")
        self.add_message(
            direction="incoming_webhook",
            sender=sender_npub,
            recipient=self._bot_npub,
            message=message,
            source="webhook",
            status="received",
        )
        event_data = {
            "entry_id": self.entry_id,
            "sender_npub": sender_npub,
            "command": command,
            "message": message,
            "payload": payload,
        }
        self.hass.bus.async_fire(f"{DOMAIN}_nostr_webhook_command", event_data)
        return event_data


class AlbyHubNostrWebhookView(HomeAssistantView):
    """Webhook endpoint for Nostr control commands."""

    url = "/api/alby_hub/nostr_webhook/{entry_id}"
    name = "api:alby_hub:nostr_webhook"
    requires_auth = False

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass

    async def post(self, request: Request, entry_id: str) -> Response:
        managers: dict[str, AlbyHubNostrBotManager] = self.hass.data.get(
            f"{DOMAIN}_nostr_managers", {}
        )
        manager = managers.get(entry_id)
        if manager is None:
            return json_response({"ok": False, "error": "entry_not_found"}, status=404)

        expected = manager.webhook_secret
        provided = (request.headers.get("X-Alby-Nostr-Secret") or "").strip()
        if not expected or provided != expected:
            return json_response({"ok": False, "error": "unauthorized"}, status=401)

        try:
            payload = await request.json()
        except Exception:  # noqa: BLE001
            return json_response({"ok": False, "error": "invalid_json"}, status=400)
        if not isinstance(payload, dict):
            return json_response({"ok": False, "error": "invalid_payload"}, status=400)

        try:
            event_data = await manager.async_handle_webhook_payload(payload)
        except PermissionError:
            return json_response({"ok": False, "error": "sender_not_whitelisted"}, status=403)
        except ValueError as err:
            return json_response({"ok": False, "error": str(err)}, status=400)
        except Exception as err:  # noqa: BLE001
            _LOGGER.warning("Nostr webhook payload processing failed: %s", err)
            return json_response({"ok": False, "error": "processing_failed"}, status=500)

        return json_response({"ok": True, "event": event_data}, status=200)


def _parse_allowed_npubs(value: str) -> set[str]:
    allowed: set[str] = set()
    for token in (value or "").replace(",", "\n").splitlines():
        clean = token.strip().lower()
        if clean:
            allowed.add(clean)
    return allowed
