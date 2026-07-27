"""Authentication: login and token lifecycle management."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime

import httpx

from .exceptions import AuthenticationError, NetworkError
from .models.auth import TokenInfo

_LOGGER = logging.getLogger(__name__)


def _md5(text: str) -> str:
    # The Siseli Cloud API requires the MD5 hash of the plaintext password.
    # This is a protocol constraint imposed by the server, not a local
    # password-storage decision.  The hash is sent over HTTPS and is never
    # stored on disk.
    return hashlib.md5(text.encode()).hexdigest()  # noqa: S324


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _extract_api_message(response: httpx.Response) -> str | None:
    """Extract a safe, short error message from an HTTP error response.

    Tries to parse the body as JSON and returns the value of the first
    recognised error field (``error``, ``message``, ``detail``).  Falls back
    to the first 200 characters of the raw text body so there is always
    *something* useful in logs.  Never returns passwords, tokens, or auth
    headers — those are never present in response bodies.
    """
    try:
        body = response.json()
        if isinstance(body, dict):
            for key in ("error", "message", "detail"):
                value = body.get(key)
                if value and isinstance(value, str):
                    return value[:200]
    except Exception:  # noqa: BLE001
        pass
    text = (response.text or "").strip()
    return text[:200] if text else None


class Auth:
    """Manages credentials and the current access token.

    The password is hashed with MD5 before being sent to the API, which
    matches the behaviour observed in the browser client.
    """

    def __init__(self, account: str, password: str) -> None:
        self._account = account
        # The web client sends the MD5 hash of the plaintext password.
        self._password_hash = _md5(password)
        self._token_info: TokenInfo | None = None

    async def login(self, http: httpx.AsyncClient) -> TokenInfo:
        """Authenticate and store the returned tokens.

        Raises :exc:`~siseli.exceptions.AuthenticationError` on HTTP-level
        auth failures (4xx).  Raises :exc:`~siseli.exceptions.NetworkError`
        on network / timeout errors so callers can distinguish the two cases.
        """
        endpoint = "/apis/login/account"
        _LOGGER.debug("Siseli auth: POST %s (account=%r)", endpoint, self._account)

        try:
            response = await http.post(
                endpoint,
                json={"account": self._account, "password": self._password_hash},
            )
        except httpx.TimeoutException as exc:
            _LOGGER.warning("Siseli auth: request timed out for account=%r", self._account)
            raise NetworkError(f"Login request timed out: {exc}") from exc
        except httpx.HTTPError as exc:
            _LOGGER.warning(
                "Siseli auth: network error for account=%r: %s", self._account, exc
            )
            raise NetworkError(f"Login request failed: {exc}") from exc

        http_status = response.status_code
        _LOGGER.debug(
            "Siseli auth: response status=%d for account=%r", http_status, self._account
        )

        # For HTTP error responses, extract a safe diagnostic message and raise
        # AuthenticationError (4xx) or NetworkError (5xx).
        if not response.is_success:
            api_message = _extract_api_message(response)
            _LOGGER.warning(
                "Siseli auth: failed for account=%r — HTTP %d%s",
                self._account,
                http_status,
                f", api_message={api_message!r}" if api_message else "",
            )
            diag = f"HTTP {http_status}"
            if api_message:
                diag = f"{diag}: {api_message}"
            if http_status >= 500:
                raise NetworkError(f"Login request failed: {diag}")
            raise AuthenticationError(
                f"Login failed: {diag}",
                http_status=http_status,
                api_message=api_message,
            )

        body = response.json()
        if body.get("code") != 0:
            api_message = body.get("message") or body.get("error") or body.get("detail")
            if api_message:
                api_message = str(api_message)
            _LOGGER.warning(
                "Siseli auth: API returned non-zero code=%r for account=%r, message=%r",
                body.get("code"),
                self._account,
                api_message,
            )
            raise AuthenticationError(
                f"Login failed (code {body.get('code')}): {api_message}",
                http_status=http_status,
                api_message=api_message,
            )

        data = body["data"]
        self._token_info = TokenInfo(
            access_token=data["accessToken"],
            refresh_token=data["refreshToken"],
            access_token_expires_at=_parse_dt(data.get("accessTokenWillExpiredAt")),
            refresh_token_expires_at=_parse_dt(data.get("refreshTokenWillExpiredAt")),
            auth_id=data.get("authId", ""),
            account=data.get("account", self._account),
            user_id=data.get("userId", ""),
        )
        _LOGGER.debug("Siseli auth: login successful for account=%r", self._account)
        return self._token_info

    @property
    def access_token(self) -> str:
        """Return the current access token.

        Raises :exc:`~siseli.exceptions.AuthenticationError` if not yet
        authenticated.
        """
        if self._token_info is None:
            raise AuthenticationError("Not authenticated — call authenticate() first")
        return self._token_info.access_token

    @property
    def token_info(self) -> TokenInfo | None:
        """Return token metadata, or *None* if not authenticated."""
        return self._token_info

    def is_authenticated(self) -> bool:
        """Return *True* when there is a valid, non-expired access token."""
        if self._token_info is None:
            return False
        expires_at = self._token_info.access_token_expires_at
        if expires_at is None:
            return True
        return datetime.now(UTC) < expires_at
