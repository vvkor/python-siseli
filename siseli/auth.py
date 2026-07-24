"""Authentication: login and token lifecycle management."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime

import httpx

from .exceptions import AuthenticationError
from .models.auth import TokenInfo


def _md5(text: str) -> str:
    return hashlib.md5(text.encode()).hexdigest()  # noqa: S324


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


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

        Raises :exc:`~siseli.exceptions.AuthenticationError` on failure.
        """
        try:
            response = await http.post(
                "/apis/login/account",
                json={"account": self._account, "password": self._password_hash},
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise AuthenticationError(f"Login request failed: {exc}") from exc

        body = response.json()
        if body.get("code") != 0:
            raise AuthenticationError(
                f"Login failed (code {body.get('code')}): {body.get('message')}"
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
