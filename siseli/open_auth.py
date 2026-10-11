"""Siseli Open API request signing helpers.

Every API request must carry IOT-Open-* headers that prove the caller holds a
valid application credential.  The signing algorithm mirrors the official web
client (CryptoJS-based) exactly:

1. Decrypt the base64-encoded app secret with AES-128-CBC.
   Key and IV are derived from MD5(app_id) as ASCII hex chars.
2. Compute a body hash: empty string for GET; SHA-256 hex for everything else.
3. Sign input: ``IOT-Open-AppID``, ``IOT-Open-Body-Hash`` and
   ``IOT-Open-Nonce`` only, sorted by key, joined as ``k=v&k=v`` without
   URL-encoding, then base64-encoded (UTF-8).
4. Sign: HMAC-SHA256(base64_string, secret) raw digest → MD5 → lowercase hex.
5. The body hash is part of the signature but is NOT sent as an HTTP header.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import uuid
from typing import TYPE_CHECKING, Any

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
        The raw query string portion of the URL. Accepted for API
        compatibility; it does not take part in the signature.
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

    # --- sign input: exactly three params, sorted, no URL-encoding -----------
    params = {
        "IOT-Open-AppID": app_id,
        "IOT-Open-Body-Hash": body_hash,
        "IOT-Open-Nonce": nonce,
    }
    signing_string = "&".join(f"{k}={v}" for k, v in sorted(params.items()))

    # --- sign: base64 -> HMAC-SHA256 (raw digest) -> MD5 hex -----------------
    base64_input = base64.b64encode(signing_string.encode("utf-8")).decode("ascii")
    hmac_digest = hmac.new(
        app_secret.encode("utf-8"),
        base64_input.encode("ascii"),
        hashlib.sha256,
    ).digest()
    sign = hashlib.md5(hmac_digest).hexdigest()  # noqa: S324

    # The body hash takes part in the signature but is not sent as a header.
    return {
        "IOT-Time-Zone": timezone,
        "IOT-Open-AppID": app_id,
        "IOT-Open-Nonce": nonce,
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
