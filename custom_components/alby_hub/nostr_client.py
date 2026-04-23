"""Minimal Nostr client helpers for encrypted DM sending."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac as _hmac
import json
import logging
import os
import time
from typing import Iterable

from aiohttp import ClientSession, ClientTimeout, WSMsgType
from nacl.bindings import crypto_aead_chacha20poly1305_ietf_encrypt

from .nwc_client import _compute_event_id, _derive_pubkey_x_hex, _ecdh_shared_x, _schnorr_sign_sync

_LOGGER = logging.getLogger(__name__)

_B32_ALPHABET = "qpzry9x8gf2tvdw0s3jn54khce6mua7l"
_B32_ALPHABET_MAP = {c: i for i, c in enumerate(_B32_ALPHABET)}
_WEBSOCKET_TIMEOUT_SECONDS = 15


def parse_key_to_hex(value: str, expected_hrp: str) -> str:
    """Parse a nostr key in hex or bech32 form and return 64-char hex."""
    raw = (value or "").strip()
    if not raw:
        raise ValueError("empty_key")
    if len(raw) == 64 and all(c in "0123456789abcdefABCDEF" for c in raw):
        return raw.lower()
    hrp, payload = _bech32_decode(raw.lower())
    if hrp != expected_hrp:
        raise ValueError(f"invalid_{expected_hrp}")
    if len(payload) != 32:
        raise ValueError("invalid_key_length")
    return payload.hex()


def npub_from_nsec(nsec_or_hex: str) -> str:
    """Derive bot npub from nsec/hex private key."""
    priv_hex = parse_key_to_hex(nsec_or_hex, "nsec")
    pub_hex = _derive_pubkey_x_hex(priv_hex)
    return _bech32_encode("npub", bytes.fromhex(pub_hex))


def nsec_from_hex(private_key_hex: str) -> str:
    """Convert a 64-char private key hex value to NSEC bech32 format."""
    priv_hex = parse_key_to_hex(private_key_hex, "nsec")
    return _bech32_encode("nsec", bytes.fromhex(priv_hex))


async def async_send_nip44_dm(
    session: ClientSession,
    relay_url: str,
    sender_nsec_or_hex: str,
    recipient_npub_or_hex: str,
    message: str,
) -> str:
    """Send NIP-44 v2 encrypted DM and return event id."""
    sender_priv_hex = parse_key_to_hex(sender_nsec_or_hex, "nsec")
    recipient_pub_hex = parse_key_to_hex(recipient_npub_or_hex, "npub")
    sender_pub_hex = _derive_pubkey_x_hex(sender_priv_hex)

    content = await asyncio.get_running_loop().run_in_executor(
        None, _nip44_encrypt_sync, sender_priv_hex, recipient_pub_hex, message
    )

    created_at = int(time.time())
    tags = [["p", recipient_pub_hex]]
    event_id = _compute_event_id(sender_pub_hex, created_at, 4, tags, content)
    sig = await asyncio.get_running_loop().run_in_executor(
        None, _schnorr_sign_sync, sender_priv_hex, event_id
    )
    event = {
        "id": event_id,
        "pubkey": sender_pub_hex,
        "created_at": created_at,
        "kind": 4,
        "tags": tags,
        "content": content,
        "sig": sig,
    }
    await _ws_publish_event(session, relay_url, event, sender_priv_hex)
    return event_id


def _nip44_encrypt_sync(sender_priv_hex: str, recipient_pub_hex: str, message: str) -> str:
    """Build a NIP-44 v2 compliant encrypted payload.

    Format: base64(version(1) | nonce(32) | ciphertext | mac(32))
    - version = 0x02
    - conversation_key = HKDF-Extract(salt=b'nip44-v2', IKM=ECDH_x)
    - nonce = 32 random bytes used as HKDF-Expand info
    - (chacha_key, chacha_nonce, hmac_key) = HKDF-Expand(conversation_key, nonce, 76)
    - ciphertext = ChaCha20-Poly1305-IETF(key=chacha_key, nonce=chacha_nonce, plaintext=padded)
    - mac = HMAC-SHA256(key=hmac_key, data=nonce | ciphertext)
    """
    shared_x = _ecdh_shared_x(sender_priv_hex, recipient_pub_hex)
    # HKDF-Extract
    conversation_key = _hmac.new(b"nip44-v2", shared_x, hashlib.sha256).digest()
    # 32-byte random nonce used as HKDF info
    nonce = os.urandom(32)
    # HKDF-Expand → 76 bytes: chacha_key(32) | chacha_nonce(12) | hmac_key(32)
    keys = _hkdf_expand_sha256(conversation_key, nonce, 76)
    chacha_key = keys[0:32]
    chacha_nonce = keys[32:44]
    hmac_key = keys[44:76]
    # Pad plaintext per NIP-44 v2
    padded = _nip44_pad(message.encode("utf-8"))
    # Encrypt (ChaCha20-Poly1305 IETF, 12-byte nonce)
    ciphertext = crypto_aead_chacha20poly1305_ietf_encrypt(padded, b"", chacha_nonce, chacha_key)
    # Authenticate nonce + ciphertext
    mac = _hmac.new(hmac_key, nonce + ciphertext, hashlib.sha256).digest()
    envelope = b"\x02" + nonce + ciphertext + mac
    return base64.b64encode(envelope).decode("ascii")


def _hkdf_expand_sha256(prk: bytes, info: bytes, length: int) -> bytes:
    """HKDF-Expand using HMAC-SHA256."""
    result = b""
    block = b""
    counter = 1
    while len(result) < length:
        block = _hmac.new(prk, block + info + bytes([counter]), hashlib.sha256).digest()
        result += block
        counter += 1
    return result[:length]


def _nip44_pad(plaintext: bytes) -> bytes:
    """NIP-44 v2 padding: 2-byte big-endian length prefix + zero-padded content."""
    length = len(plaintext)
    if length == 0 or length > 65535:
        raise ValueError("nip44_invalid_plaintext_length")
    if length <= 32:
        chunk = 32
    else:
        next_power = 1 << (length - 1).bit_length()
        chunk = 64 if next_power <= 64 else next_power
    return length.to_bytes(2, "big") + plaintext + b"\x00" * (chunk - length)


async def _ws_publish_event(
    session: ClientSession,
    relay_url: str,
    event: dict,
    sender_priv_hex: str | None = None,
) -> None:
    """Publish a signed Nostr event over a WebSocket connection.

    Handles NIP-42 AUTH challenges automatically when *sender_priv_hex* is
    provided so that relays that require authentication (such as
    wss://relay.getalby.com/v1) accept the event.
    """
    timeout = ClientTimeout(total=_WEBSOCKET_TIMEOUT_SECONDS)
    event_id = event["id"]
    async with session.ws_connect(relay_url, timeout=timeout) as ws:
        await ws.send_str(json.dumps(["EVENT", event]))
        deadline = time.monotonic() + 10
        auth_sent = False
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                return
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=remaining)
            except asyncio.TimeoutError:
                return
            if msg.type != WSMsgType.TEXT:
                if msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    return
                continue
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, list) or not data:
                continue
            msg_type = data[0]
            if msg_type == "AUTH" and len(data) >= 2 and sender_priv_hex and not auth_sent:
                # NIP-42: respond to authentication challenge
                challenge = str(data[1])
                auth_event = await _build_nip42_auth_event(
                    sender_priv_hex, relay_url, challenge
                )
                await ws.send_str(json.dumps(["AUTH", auth_event]))
                auth_sent = True
                # Re-send the original event now that we are authenticated
                await ws.send_str(json.dumps(["EVENT", event]))
            elif msg_type == "OK" and len(data) >= 3 and data[1] == event_id:
                if data[2] is True:
                    return  # Success
                raise ValueError(
                    f"Relay rejected event: {data[3] if len(data) >= 4 else 'unknown'}"
                )


async def _build_nip42_auth_event(
    sender_priv_hex: str,
    relay_url: str,
    challenge: str,
) -> dict:
    """Build and sign a NIP-42 kind-22242 AUTH event."""
    sender_pub_hex = _derive_pubkey_x_hex(sender_priv_hex)
    created_at = int(time.time())
    tags = [["relay", relay_url], ["challenge", challenge]]
    event_id = _compute_event_id(sender_pub_hex, created_at, 22242, tags, "")
    sig = await asyncio.get_running_loop().run_in_executor(
        None, _schnorr_sign_sync, sender_priv_hex, event_id
    )
    return {
        "id": event_id,
        "pubkey": sender_pub_hex,
        "created_at": created_at,
        "kind": 22242,
        "tags": tags,
        "content": "",
        "sig": sig,
    }


def _bech32_decode(value: str) -> tuple[str, bytes]:
    if "1" not in value:
        raise ValueError("invalid_bech32")
    pos = value.rfind("1")
    hrp = value[:pos]
    data_part = value[pos + 1 :]
    if not hrp or len(data_part) < 7:
        raise ValueError("invalid_bech32")
    values = []
    for c in data_part:
        if c not in _B32_ALPHABET_MAP:
            raise ValueError("invalid_bech32")
        values.append(_B32_ALPHABET_MAP[c])
    if not _bech32_verify_checksum(hrp, values):
        raise ValueError("invalid_bech32_checksum")
    payload_5bit = values[:-6]
    payload = bytes(_convertbits(payload_5bit, 5, 8, False))
    return hrp, payload


def _bech32_encode(hrp: str, payload: bytes) -> str:
    data = list(_convertbits(payload, 8, 5, True))
    checksum = _bech32_create_checksum(hrp, data)
    return f"{hrp}1{''.join(_B32_ALPHABET[d] for d in data + checksum)}"


def _bech32_polymod(values: Iterable[int]) -> int:
    generators = [0x3B6A57B2, 0x26508E6D, 0x1EA119FA, 0x3D4233DD, 0x2A1462B3]
    chk = 1
    for value in values:
        top = chk >> 25
        chk = ((chk & 0x1FFFFFF) << 5) ^ value
        for i, g in enumerate(generators):
            if (top >> i) & 1:
                chk ^= g
    return chk


def _bech32_hrp_expand(hrp: str) -> list[int]:
    return [ord(c) >> 5 for c in hrp] + [0] + [ord(c) & 31 for c in hrp]


def _bech32_verify_checksum(hrp: str, data: list[int]) -> bool:
    return _bech32_polymod(_bech32_hrp_expand(hrp) + data) == 1


def _bech32_create_checksum(hrp: str, data: list[int]) -> list[int]:
    values = _bech32_hrp_expand(hrp) + data
    polymod = _bech32_polymod(values + [0, 0, 0, 0, 0, 0]) ^ 1
    return [(polymod >> 5 * (5 - i)) & 31 for i in range(6)]


def _convertbits(data: Iterable[int], frombits: int, tobits: int, pad: bool) -> list[int]:
    acc = 0
    bits = 0
    ret: list[int] = []
    maxv = (1 << tobits) - 1
    max_acc = (1 << (frombits + tobits - 1)) - 1
    for value in data:
        if value < 0 or (value >> frombits):
            raise ValueError("invalid_convertbits_value")
        acc = ((acc << frombits) | value) & max_acc
        bits += frombits
        while bits >= tobits:
            bits -= tobits
            ret.append((acc >> bits) & maxv)
    if pad:
        if bits:
            ret.append((acc << (tobits - bits)) & maxv)
    elif bits >= frombits or ((acc << (tobits - bits)) & maxv):
        raise ValueError("invalid_convertbits_padding")
    return ret
