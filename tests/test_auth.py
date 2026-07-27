"""Tests for diagnostic logging and error handling in Auth.login()."""

from __future__ import annotations

import pytest
import httpx

from siseli.auth import Auth, _extract_api_message
from siseli.exceptions import AuthenticationError, NetworkError


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOD_BODY = {
    "code": 0,
    "data": {
        "accessToken": "tok-access",
        "refreshToken": "tok-refresh",
        "accessTokenWillExpiredAt": None,
        "refreshTokenWillExpiredAt": None,
        "authId": "auth-1",
        "account": "user@example.com",
        "userId": "uid-1",
    },
}


def _make_response(status_code: int, json_body: object | None = None, text: str = "") -> httpx.Response:
    """Build a minimal fake httpx.Response."""
    import json as _json

    if json_body is not None:
        content = _json.dumps(json_body).encode()
        headers = {"content-type": "application/json"}
    else:
        content = text.encode()
        headers = {"content-type": "text/plain"}

    return httpx.Response(
        status_code=status_code,
        content=content,
        headers=headers,
        request=httpx.Request("POST", "https://example.com/apis/login/account"),
    )


class _FakeAsyncClient:
    """Minimal async HTTP client stub."""

    def __init__(self, response: httpx.Response | Exception) -> None:
        self._response = response
        self.last_request_json: dict | None = None

    async def post(self, url: str, *, json: dict | None = None, **_: object) -> httpx.Response:
        self.last_request_json = json
        if isinstance(self._response, Exception):
            raise self._response
        return self._response


# ---------------------------------------------------------------------------
# _extract_api_message
# ---------------------------------------------------------------------------


def test_extract_api_message_json_error_field() -> None:
    resp = _make_response(401, json_body={"error": "invalid_credentials"})
    assert _extract_api_message(resp) == "invalid_credentials"


def test_extract_api_message_json_message_field() -> None:
    resp = _make_response(401, json_body={"message": "Bad password"})
    assert _extract_api_message(resp) == "Bad password"


def test_extract_api_message_json_detail_field() -> None:
    resp = _make_response(403, json_body={"detail": "Account locked"})
    assert _extract_api_message(resp) == "Account locked"


def test_extract_api_message_prefers_error_over_message() -> None:
    resp = _make_response(401, json_body={"error": "first", "message": "second"})
    assert _extract_api_message(resp) == "first"


def test_extract_api_message_plain_text_fallback() -> None:
    resp = _make_response(500, text="Internal Server Error")
    assert _extract_api_message(resp) == "Internal Server Error"


def test_extract_api_message_truncates_long_text() -> None:
    long_text = "x" * 300
    resp = _make_response(500, text=long_text)
    result = _extract_api_message(resp)
    assert result is not None
    assert len(result) == 200


def test_extract_api_message_empty_body() -> None:
    resp = _make_response(401, text="")
    assert _extract_api_message(resp) is None


# ---------------------------------------------------------------------------
# Auth.login — HTTP error status codes
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_401_raises_authentication_error_with_status() -> None:
    response = _make_response(401, json_body={"error": "invalid_credentials"})
    client = _FakeAsyncClient(response)

    auth = Auth("user@example.com", "secret")
    with pytest.raises(AuthenticationError) as exc_info:
        await auth.login(client)

    err = exc_info.value
    assert err.http_status == 401
    assert err.api_message == "invalid_credentials"
    assert "401" in str(err)
    assert "invalid_credentials" in str(err)


@pytest.mark.asyncio
async def test_login_403_raises_authentication_error() -> None:
    response = _make_response(403, json_body={"message": "Account disabled"})
    client = _FakeAsyncClient(response)

    auth = Auth("user@example.com", "secret")
    with pytest.raises(AuthenticationError) as exc_info:
        await auth.login(client)

    err = exc_info.value
    assert err.http_status == 403
    assert err.api_message == "Account disabled"
    assert "403" in str(err)


@pytest.mark.asyncio
async def test_login_429_raises_authentication_error() -> None:
    response = _make_response(429, json_body={"message": "Too Many Requests"})
    client = _FakeAsyncClient(response)

    auth = Auth("user@example.com", "secret")
    with pytest.raises(AuthenticationError) as exc_info:
        await auth.login(client)

    err = exc_info.value
    assert err.http_status == 429
    assert err.api_message == "Too Many Requests"


@pytest.mark.asyncio
async def test_login_5xx_raises_network_error() -> None:
    response = _make_response(503, json_body={"error": "Service unavailable"})
    client = _FakeAsyncClient(response)

    auth = Auth("user@example.com", "secret")
    with pytest.raises(NetworkError) as exc_info:
        await auth.login(client)

    assert "503" in str(exc_info.value)


@pytest.mark.asyncio
async def test_login_500_raises_network_error_not_auth_error() -> None:
    response = _make_response(500, text="Internal Server Error")
    client = _FakeAsyncClient(response)

    auth = Auth("user@example.com", "secret")
    with pytest.raises(NetworkError):
        await auth.login(client)


# ---------------------------------------------------------------------------
# Auth.login — network / timeout errors
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_timeout_raises_network_error() -> None:
    client = _FakeAsyncClient(httpx.TimeoutException("timed out"))

    auth = Auth("user@example.com", "secret")
    with pytest.raises(NetworkError) as exc_info:
        await auth.login(client)

    assert "timed out" in str(exc_info.value).lower() or "timeout" in str(exc_info.value).lower()


@pytest.mark.asyncio
async def test_login_connection_error_raises_network_error() -> None:
    client = _FakeAsyncClient(httpx.ConnectError("connection refused"))

    auth = Auth("user@example.com", "secret")
    with pytest.raises(NetworkError):
        await auth.login(client)


# ---------------------------------------------------------------------------
# Auth.login — non-zero API code (HTTP 200 but code != 0)
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_api_nonzero_code_raises_auth_error() -> None:
    response = _make_response(200, json_body={"code": 10001, "message": "Wrong credentials"})
    client = _FakeAsyncClient(response)

    auth = Auth("user@example.com", "secret")
    with pytest.raises(AuthenticationError) as exc_info:
        await auth.login(client)

    err = exc_info.value
    assert err.http_status == 200
    assert err.api_message == "Wrong credentials"
    assert "10001" in str(err)
    assert "Wrong credentials" in str(err)


# ---------------------------------------------------------------------------
# Auth.login — no secrets in error messages
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_error_message_does_not_contain_password() -> None:
    response = _make_response(401, json_body={"error": "invalid_credentials"})
    client = _FakeAsyncClient(response)

    password = "s3cr3tpassword"
    auth = Auth("user@example.com", password)
    with pytest.raises(AuthenticationError) as exc_info:
        await auth.login(client)

    assert password not in str(exc_info.value)
    # MD5 hash should not appear either (it's the sent value, not in response)
    import hashlib
    md5_hash = hashlib.md5(password.encode()).hexdigest()  # noqa: S324
    assert md5_hash not in str(exc_info.value)


@pytest.mark.asyncio
async def test_login_request_does_not_send_plaintext_password() -> None:
    """Verify the login request sends MD5 hash, not the plaintext password."""
    response = _make_response(200, json_body=_GOOD_BODY)
    client = _FakeAsyncClient(response)

    password = "plaintext_password"
    auth = Auth("user@example.com", password)
    await auth.login(client)

    assert client.last_request_json is not None
    assert client.last_request_json.get("password") != password


# ---------------------------------------------------------------------------
# Auth.login — successful login
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_login_success_returns_token_info() -> None:
    response = _make_response(200, json_body=_GOOD_BODY)
    client = _FakeAsyncClient(response)

    auth = Auth("user@example.com", "secret")
    token_info = await auth.login(client)

    assert token_info.access_token == "tok-access"
    assert token_info.refresh_token == "tok-refresh"
    assert auth.is_authenticated()


# ---------------------------------------------------------------------------
# AuthenticationError attributes
# ---------------------------------------------------------------------------


def test_authentication_error_attributes() -> None:
    err = AuthenticationError(
        "Login failed: HTTP 401: invalid_credentials",
        http_status=401,
        api_message="invalid_credentials",
    )
    assert err.http_status == 401
    assert err.api_message == "invalid_credentials"
    assert "401" in str(err)


def test_authentication_error_defaults() -> None:
    err = AuthenticationError("Not authenticated")
    assert err.http_status is None
    assert err.api_message is None
