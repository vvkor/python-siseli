"""Siseli Open API request signing helpers.

Every API request must carry IOT-Open-* headers that prove the caller holds a
valid application credential.  The signing algorithm mirrors the official web
client (CryptoJS-based) exactly:

1. Decrypt the base64-encoded app secret with AES-128-CBC.
   Key and IV are derived from MD5(app_id) as ASCII hex chars.
2. Compute a body hash: empty string for GET; SHA-256 hex for everything else.
3. Collect query params, inject the three open-auth fields, sort by key,
   serialise without URL-encoding, hex-encode the UTF-8 bytes.
4. Sign: HMAC-SHA256(hex_string, secret) → MD5 → lowercase hex.
"""

from __future__ import annotations

import hashlib
import hmac
import uuid
from typing import TYPE_CHECKING, Any
from urllib.parse import parse_qs

from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes

from .const import SISELI_APP_ID, SISELI_APP_SECRET_ENCRYPTED

if TYPE_CHECKING:
    import httpx


def decrypt_open_secret(app_id: str, encrypted_secret_b64: str) -> str:
    """Decrypt the base64-encoded app secret using AES-128-CBC.

    The AES key and IV are derived from MD5(app_id).lower():
    - first 16 hex chars → 16 ASCII bytes → AES key
    - last  16 hex chars → 16 ASCII bytes → IV

    ZeroPadding is assumed: trailing null bytes are stripped from the output.
    """
    import base64

    md5_hex = hashlib.md5(app_id.encode()).hexdigest()  # noqa: S324
    key = md5_hex[:16].encode("ascii")
    iv = md5_hex[16:].encode("ascii")

    encrypted_bytes = base64.b64decode(encrypted_secret_b64)
    cipher = Cipher(algorithms.AES(key), modes.CBC(iv))
    decryptor = cipher.decryptor()
    plaintext = decryptor.update(encrypted_bytes) + decryptor.finalize()
    return plaintext.rstrip(b"\x00").decode("utf-8")


def _sha256_hex(data: bytes) -> str:
    """Return the lowercase hex SHA-256 digest of *data*."""
    return hashlib.sha256(data).hexdigest()


def build_open_headers(
    *,
    method: str,
    query: str,
    body: bytes | None,
    app_id: str,
    app_secret: str,
    timezone: str,
    nonce: str,
) -> dict[str, str]:
    """Build the IOT-Open-* headers (and IOT-Time-Zone) for a single request.

    Parameters
    ----------
    method:
        HTTP method ("GET", "POST", …).
    query:
        The raw query string portion of the URL (without the leading "?").
    body:
        Raw request body bytes, or *None* / empty for GET requests.
    app_id:
        The application ID (``IOT-Open-AppID``).
    app_secret:
        The *decrypted* application secret used as the HMAC key.
    timezone:
        The client timezone string, e.g. "UTC" or "Europe/Moscow".
    nonce:
        A unique string per request (UUID hex recommended).
    """
    # --- body hash -----------------------------------------------------------
    if method.upper() == "GET":
        body_hash = ""
    else:
        body_hash = _sha256_hex(body if body else b"")

    # --- params for the sign input -------------------------------------------
    params: dict[str, str] = {}
    if query:
        for key, values in parse_qs(query, keep_blank_values=True).items():
            params[key] = values[0]

    # Remove any stale open-auth fields so they cannot influence the new sign.
    for field in ("IOT-Open-AppID", "IOT-Open-Nonce", "IOT-Open-Sign", "IOT-Open-Body-Hash"):
        params.pop(field, None)

    params["IOT-Open-AppID"] = app_id
    params["IOT-Open-Nonce"] = nonce
    params["IOT-Open-Body-Hash"] = body_hash

    # Sort alphabetically (case-sensitive, matching JS default sort order).
    query_str = "&".join(f"{k}={v}" for k, v in sorted(params.items()))

    # --- sign ----------------------------------------------------------------
    # CryptoJS: Utf8.parse(query_str) → Hex.stringify → hex_string
    # Then: HmacSHA256(hex_string, secret) → MD5 → hex
    hex_str = query_str.encode("utf-8").hex()
    hmac_digest = hmac.new(
        app_secret.encode("utf-8"),
        hex_str.encode("utf-8"),
        hashlib.sha256,
    ).digest()
    sign = hashlib.md5(hmac_digest).hexdigest()  # noqa: S324

    return {
        "IOT-Time-Zone": timezone,
        "IOT-Open-AppID": app_id,
        "IOT-Open-Nonce": nonce,
        "IOT-Open-Body-Hash": body_hash,
        "IOT-Open-Sign": sign,
    }


def attach_open_auth(
    client: Any,
    *,
    app_id: str = SISELI_APP_ID,
    encrypted_secret: str = SISELI_APP_SECRET_ENCRYPTED,
) -> None:
    """Attach an httpx request hook that adds Open API signing headers.

    The hook is appended to ``client._http.event_hooks["request"]`` and runs
    before every outgoing request, injecting:

    - ``IOT-Time-Zone``
    - ``IOT-Open-AppID``
    - ``IOT-Open-Nonce``
    - ``IOT-Open-Body-Hash``
    - ``IOT-Open-Sign``

    Parameters
    ----------
    client:
        A :class:`~siseli.SiseliClient` instance (or any object with
        ``._http.event_hooks`` and ``._timezone``).
    app_id:
        Override the default production App ID.
    encrypted_secret:
        Override the default production encrypted secret.
    """
    secret = decrypt_open_secret(app_id, encrypted_secret)
    timezone = getattr(client, "_timezone", "UTC")

    async def _sign_request(request: "httpx.Request") -> None:
        nonce = uuid.uuid4().hex
        query = request.url.query
        if isinstance(query, bytes):
            query = query.decode("utf-8")
        body = request.content if request.method.upper() != "GET" else None
        headers = build_open_headers(
            method=request.method,
            query=query,
            body=body,
            app_id=app_id,
            app_secret=secret,
            timezone=timezone,
            nonce=nonce,
        )
        request.headers.update(headers)

    client._http.event_hooks["request"].append(_sign_request)
