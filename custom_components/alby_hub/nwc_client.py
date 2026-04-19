"""Nostr Wallet Connect (NWC) client – async, WebSocket relay-based.

Implements NIP-04 encryption and BIP-340 Schnorr signing so that NWC
``get_info`` and ``get_balance`` requests can be made from Cloud mode
without a local Alby Hub API.

Crypto notes
------------
* ECDH shared-key derivation uses the Python ``cryptography`` library
  (OpenSSL under the hood → fast C code).
* BIP-340 Schnorr signing is a pure-Python implementation and is run in
  a thread-pool executor to avoid blocking the HA event loop.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import json
import logging
import os
import time
from typing import Any

from aiohttp import ClientSession, ClientTimeout, WSMsgType
from cryptography.hazmat.primitives.asymmetric.ec import (
    ECDH,
    SECP256K1,
    EllipticCurvePublicKey,
    derive_private_key,
)
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat

from .nwc import NwcConnectionInfo

_LOGGER = logging.getLogger(__name__)

# ── secp256k1 curve parameters ─────────────────────────────────────────────
_P = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEFFFFFC2F
_N = 0xFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFFEBAAEDCE6AF48A03BBFD25E8CD0364141
_GX = 0x79BE667EF9DCBBAC55A06295CE870B07029BFCDB2DCE28D959F2815B16F81798
_GY = 0x483ADA7726A3C4655DA4FBFC0E1108A8FD17B448A68554199C47D08FFB10D4B8
_G: tuple[int, int] = (_GX, _GY)

# ── Nostr / NWC constants ──────────────────────────────────────────────────
_KIND_REQUEST = 23194
_KIND_RESPONSE = 23195
_WS_TIMEOUT = 15  # seconds


# ── secp256k1 EC arithmetic (pure Python, executed in thread pool) ─────────

def _point_add(
    P: tuple[int, int] | None,
    Q: tuple[int, int] | None,
) -> tuple[int, int] | None:
    if P is None:
        return Q
    if Q is None:
        return P
    px, py = P
    qx, qy = Q
    if px == qx:
        if py != qy:
            return None  # point at infinity
        lam = 3 * px * px * pow(2 * py, _P - 2, _P) % _P
    else:
        lam = (qy - py) * pow(qx - px, _P - 2, _P) % _P
    rx = (lam * lam - px - qx) % _P
    return rx, (lam * (px - rx) - py) % _P


def _point_mul(P: tuple[int, int], k: int) -> tuple[int, int] | None:
    R: tuple[int, int] | None = None
    Q = P
    while k:
        if k & 1:
            R = _point_add(R, Q)
        Q = _point_add(Q, Q)
        k >>= 1
    return R


def _tagged_hash(tag: str, data: bytes) -> bytes:
    h = hashlib.sha256(tag.encode()).digest()
    return hashlib.sha256(h + h + data).digest()


def _schnorr_sign_sync(privkey_hex: str, msg_hex: str) -> str:
    """BIP-340 Schnorr sign – returns 64-byte signature as lower-case hex.

    This is the CPU-intensive pure-Python path. Always call via executor so
    it does not block the HA event loop.
    """
    msg = bytes.fromhex(msg_hex)
    d0 = int(privkey_hex, 16)
    P = _point_mul(_G, d0)
    if P is None:
        raise ValueError("Private key is zero or maps to point at infinity")
    d = d0 if P[1] % 2 == 0 else _N - d0
    rand = os.urandom(32)
    t = (d ^ int.from_bytes(_tagged_hash("BIP0340/nonce", rand), "big")).to_bytes(32, "big")
    k0 = (
        int.from_bytes(
            _tagged_hash("BIP0340/nonce", t + P[0].to_bytes(32, "big") + msg), "big"
        )
        % _N
    )
    if k0 == 0:
        raise ValueError("k0 is zero – retry")
    R = _point_mul(_G, k0)
    if R is None:
        raise ValueError("R is point at infinity")
    k = k0 if R[1] % 2 == 0 else _N - k0
    e = (
        int.from_bytes(
            _tagged_hash(
                "BIP0340/challenge",
                R[0].to_bytes(32, "big") + P[0].to_bytes(32, "big") + msg,
            ),
            "big",
        )
        % _N
    )
    sig = R[0].to_bytes(32, "big") + ((k + e * d) % _N).to_bytes(32, "big")
    return sig.hex()


# ── NIP-04 ECDH + AES helpers (OpenSSL via cryptography lib – fast) ────────

def _ecdh_shared_x(privkey_hex: str, pubkey_hex: str) -> bytes:
    """Derive 32-byte NIP-04 shared key via ECDH x-coordinate."""
    privkey_int = int(privkey_hex, 16)
    private_key = derive_private_key(privkey_int, SECP256K1())
    # Nostr pubkeys are x-only (32 bytes); assume even parity (0x02 prefix)
    compressed = bytes.fromhex("02" + pubkey_hex)
    server_key = EllipticCurvePublicKey.from_encoded_point(SECP256K1(), compressed)
    return private_key.exchange(ECDH(), server_key)


def _nip04_encrypt(plaintext: str, shared_key: bytes) -> str:
    data = plaintext.encode()
    pad = 16 - len(data) % 16
    data += bytes([pad] * pad)
    iv = os.urandom(16)
    cipher = Cipher(algorithms.AES(shared_key), modes.CBC(iv))
    enc = cipher.encryptor()
    ct = enc.update(data) + enc.finalize()
    return base64.b64encode(ct).decode() + "?iv=" + base64.b64encode(iv).decode()


def _nip04_decrypt(encrypted: str, shared_key: bytes) -> str:
    ct_b64, iv_b64 = encrypted.split("?iv=", 1)
    ct = base64.b64decode(ct_b64)
    iv = base64.b64decode(iv_b64)
    cipher = Cipher(algorithms.AES(shared_key), modes.CBC(iv))
    dec = cipher.decryptor()
    padded = dec.update(ct) + dec.finalize()
    return padded[: -padded[-1]].decode()


# ── Nostr event helpers ─────────────────────────────────────────────────────

def _derive_pubkey_x_hex(privkey_hex: str) -> str:
    """Derive 32-byte x-only public key hex from private key hex."""
    privkey_int = int(privkey_hex, 16)
    private_key = derive_private_key(privkey_int, SECP256K1())
    raw = private_key.public_key().public_bytes(Encoding.X962, PublicFormat.CompressedPoint)
    return raw[1:].hex()  # drop 02/03 prefix → 32-byte x-only


def _compute_event_id(
    pubkey: str, created_at: int, kind: int, tags: list, content: str
) -> str:
    serialized = json.dumps(
        [0, pubkey, created_at, kind, tags, content],
        separators=(",", ":"),
        ensure_ascii=False,
    )
    return hashlib.sha256(serialized.encode()).hexdigest()


# ── Public async API ────────────────────────────────────────────────────────

async def async_nwc_request(
    session: ClientSession,
    nwc_info: NwcConnectionInfo,
    method: str,
    params: dict | None = None,
) -> dict[str, Any] | None:
    """Send a NWC request to the relay and return the decrypted response dict.

    Returns ``None`` on any failure (network, crypto, timeout).  Errors are
    logged at DEBUG level only so they do not flood the HA log.
    """
    if params is None:
        params = {}

    try:
        client_pubkey = _derive_pubkey_x_hex(nwc_info.secret)
        shared_key = _ecdh_shared_x(nwc_info.secret, nwc_info.wallet_pubkey)
    except Exception as err:
        _LOGGER.debug("NWC crypto setup failed for %s: %s", method, err)
        return None

    payload = json.dumps({"method": method, "params": params})
    try:
        encrypted_content = _nip04_encrypt(payload, shared_key)
    except Exception as err:
        _LOGGER.debug("NIP-04 encrypt failed for %s: %s", method, err)
        return None

    created_at = int(time.time())
    tags = [["p", nwc_info.wallet_pubkey]]
    eid = _compute_event_id(client_pubkey, created_at, _KIND_REQUEST, tags, encrypted_content)

    # Schnorr signing is CPU-intensive pure Python → run in thread pool
    loop = asyncio.get_running_loop()
    try:
        sig = await loop.run_in_executor(None, _schnorr_sign_sync, nwc_info.secret, eid)
    except Exception as err:
        _LOGGER.debug("Schnorr signing failed for %s: %s", method, err)
        return None

    event = {
        "id": eid,
        "pubkey": client_pubkey,
        "created_at": created_at,
        "kind": _KIND_REQUEST,
        "tags": tags,
        "content": encrypted_content,
        "sig": sig,
    }

    try:
        return await _ws_exchange(
            session, nwc_info.relay, event, eid, shared_key, client_pubkey
        )
    except Exception as err:
        _LOGGER.debug("NWC WebSocket request %s failed: %s", method, err)
        return None


async def _ws_exchange(
    session: ClientSession,
    relay_url: str,
    event: dict,
    event_id: str,
    shared_key: bytes,
    client_pubkey: str,
) -> dict[str, Any] | None:
    """Open a WebSocket connection, publish *event*, and await the NWC response."""
    sub_id = event_id[:16]
    timeout = ClientTimeout(total=_WS_TIMEOUT)
    loop = asyncio.get_running_loop()

    async with session.ws_connect(relay_url, timeout=timeout) as ws:
        # Subscribe before publishing to avoid missing early responses
        await ws.send_str(
            json.dumps([
                "REQ",
                sub_id,
                {
                    "kinds": [_KIND_RESPONSE],
                    "#p": [client_pubkey],
                    "#e": [event_id],
                },
            ])
        )
        await ws.send_str(json.dumps(["EVENT", event]))

        deadline = time.monotonic() + _WS_TIMEOUT
        while True:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                break
            try:
                msg = await asyncio.wait_for(ws.receive(), timeout=remaining)
            except asyncio.TimeoutError:
                break
            if msg.type != WSMsgType.TEXT:
                if msg.type in (WSMsgType.ERROR, WSMsgType.CLOSE):
                    break
                continue
            try:
                data = json.loads(msg.data)
            except json.JSONDecodeError:
                continue
            if not isinstance(data, list) or len(data) < 3 or data[0] != "EVENT":
                continue
            nostr_event = data[2]
            if not isinstance(nostr_event, dict):
                continue
            if nostr_event.get("kind") != _KIND_RESPONSE:
                continue
            # Verify the response references our request event
            ref = next(
                (t[1] for t in nostr_event.get("tags", []) if len(t) >= 2 and t[0] == "e"),
                None,
            )
            if ref != event_id:
                continue
            try:
                decrypted = await loop.run_in_executor(
                    None, _nip04_decrypt, nostr_event["content"], shared_key
                )
                return json.loads(decrypted)
            except Exception as err:
                _LOGGER.debug("NIP-04 decrypt failed: %s", err)
                continue

    return None
