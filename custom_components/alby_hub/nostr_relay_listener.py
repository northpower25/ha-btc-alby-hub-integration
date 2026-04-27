"""Nostr relay listener – subscribes to incoming DMs for the bot key."""

from __future__ import annotations

import asyncio
import json
import logging
import time
from typing import TYPE_CHECKING

from aiohttp import ClientSession, ClientTimeout, ClientWebSocketResponse, WSMsgType

from .nostr_client import _bech32_encode, try_decrypt_dm

if TYPE_CHECKING:
    from .nostr_bot import AlbyHubNostrBotManager

_LOGGER = logging.getLogger(__name__)

_INITIAL_BACKOFF = 5      # seconds before first reconnect attempt
_MAX_BACKOFF = 60         # maximum backoff cap
_CONNECT_TIMEOUT = 15     # seconds for the TCP/TLS handshake
_PING_INTERVAL = 30       # WebSocket heartbeat interval
# How far back (in seconds) to request missed messages on first connect
_LOOKBACK_SECONDS = 600   # 10 minutes

_SUB_ID = "alby_hub_bot_inbox"


class NostrRelayListener:
    """Listens on configured relays for kind:4 DMs addressed to the bot.

    Relays are connected independently; each uses its own reconnect loop
    with exponential back-off.  Successfully decrypted messages (NIP-44
    first, then NIP-04 as fallback) are handed off to the
    :class:`~.nostr_bot.AlbyHubNostrBotManager` for in-memory storage
    and Home Assistant event firing.
    """

    def __init__(
        self,
        session: ClientSession,
        manager: "AlbyHubNostrBotManager",
        relay_urls: list[str],
        bot_priv_hex: str,
        bot_pub_hex: str,
    ) -> None:
        self._session = session
        self._manager = manager
        self._relay_urls = relay_urls
        self._bot_priv_hex = bot_priv_hex
        self._bot_pub_hex = bot_pub_hex
        self._tasks: list[asyncio.Task] = []
        self._running = False
        self._seen_event_ids: set[str] = set()  # global dedup across all relays

    async def async_start(self) -> None:
        """Start one listener task per relay URL."""
        if self._running:
            return
        self._running = True
        for relay_url in self._relay_urls:
            task = asyncio.create_task(
                self._relay_loop(relay_url),
                name=f"nostr_listener_{relay_url}",
            )
            self._tasks.append(task)
        _LOGGER.debug(
            "Nostr relay listener started for %d relay(s): %s",
            len(self._relay_urls),
            self._relay_urls,
        )

    async def async_stop(self) -> None:
        """Cancel all listener tasks and wait for them to finish."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self._seen_event_ids.clear()
        _LOGGER.debug("Nostr relay listener stopped")

    # ── Internal ──────────────────────────────────────────────────────────────

    async def _relay_loop(self, relay_url: str) -> None:
        """Persistent loop for a single relay: connect, listen, reconnect."""
        backoff = _INITIAL_BACKOFF
        while self._running:
            try:
                await self._connect_and_listen(relay_url)
                # Clean disconnect (relay closed or EOSE with no further events)
                backoff = _INITIAL_BACKOFF
            except asyncio.CancelledError:
                return
            except Exception as exc:  # noqa: BLE001
                _LOGGER.debug(
                    "Relay listener %s: error – %s – reconnecting in %ss",
                    relay_url,
                    exc,
                    backoff,
                )

            if not self._running:
                return
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, _MAX_BACKOFF)

    async def _connect_and_listen(self, relay_url: str) -> None:
        """Open a WebSocket connection to *relay_url*, subscribe, and process events."""
        timeout = ClientTimeout(connect=_CONNECT_TIMEOUT, sock_read=None, total=None)
        since = int(time.time()) - _LOOKBACK_SECONDS
        sub_filter = {
            "kinds": [4],
            "#p": [self._bot_pub_hex],
            "since": since,
        }
        req_msg = json.dumps(["REQ", _SUB_ID, sub_filter])
        seen_ids: set[str] = set()  # per-connection dedup (relay echo/resubscribe guard)

        async with self._session.ws_connect(
            relay_url,
            timeout=timeout,
            heartbeat=_PING_INTERVAL,
            ssl=None,
        ) as ws:
            _LOGGER.debug("Nostr listener connected to %s (since=%s)", relay_url, since)
            await ws.send_str(req_msg)

            async for msg in ws:
                if not self._running:
                    await ws.close()
                    return
                if msg.type == WSMsgType.ERROR:
                    raise RuntimeError(f"WebSocket error: {msg.data}")
                if msg.type == WSMsgType.CLOSE:
                    return
                if msg.type != WSMsgType.TEXT:
                    continue

                try:
                    data = json.loads(msg.data)
                except json.JSONDecodeError:
                    continue

                if not isinstance(data, list) or not data:
                    continue

                msg_type = data[0]

                if msg_type == "AUTH" and len(data) >= 2:
                    await self._handle_auth(ws, relay_url, str(data[1]))
                    # Re-subscribe after authentication
                    await ws.send_str(req_msg)

                elif msg_type == "EVENT" and len(data) >= 3:
                    event = data[2]
                    if not isinstance(event, dict):
                        continue
                    event_id = event.get("id", "")
                    if event_id in seen_ids:
                        continue
                    seen_ids.add(event_id)
                    if event_id and event_id in self._seen_event_ids:
                        continue
                    if event_id:
                        self._seen_event_ids.add(event_id)
                    self._handle_event(event)

    async def _handle_auth(self, ws: ClientWebSocketResponse, relay_url: str, challenge: str) -> None:
        """Respond to a NIP-42 AUTH challenge."""
        from .nostr_client import _build_nip42_auth_event  # noqa: PLC0415
        try:
            auth_event = await _build_nip42_auth_event(
                self._bot_priv_hex, relay_url, challenge
            )
            await ws.send_str(json.dumps(["AUTH", auth_event]))
            _LOGGER.debug("Sent NIP-42 AUTH response to %s", relay_url)
        except Exception as exc:  # noqa: BLE001
            _LOGGER.debug("Failed to build/send NIP-42 AUTH for %s: %s", relay_url, exc)

    def _handle_event(self, event: dict) -> None:
        """Decrypt and record a kind:4 event received from a relay."""
        sender_pub_hex: str = event.get("pubkey", "")
        content: str = event.get("content", "")
        created_at: int = event.get("created_at", 0)
        kind: int = event.get("kind", 0)

        if kind != 4 or not sender_pub_hex or not content:
            return

        # Do not record events the bot sent (we already track those locally)
        if sender_pub_hex == self._bot_pub_hex:
            return

        try:
            plaintext, method = try_decrypt_dm(self._bot_priv_hex, sender_pub_hex, content)
        except ValueError as exc:
            _LOGGER.debug(
                "Relay listener: could not decrypt event from %s…: %s",
                sender_pub_hex[:16],
                exc,
            )
            return

        sender_npub = _bech32_encode("npub", bytes.fromhex(sender_pub_hex))

        self._manager.add_message(
            direction="incoming",
            sender=sender_npub,
            recipient=self._manager.bot_npub,
            message=plaintext,
            source=f"relay:{method}",
            status="received",
        )

        # Fire an HA bus event when the sender is whitelisted
        if self._manager.is_allowed_npub(sender_npub):
            self._manager.hass.bus.async_fire(
                f"alby_hub_nostr_webhook_command",
                {
                    "entry_id": self._manager.entry_id,
                    "sender_npub": sender_npub,
                    "command": plaintext,
                    "message": plaintext,
                    "source": f"relay:{method}",
                    "created_at": created_at,
                },
            )
