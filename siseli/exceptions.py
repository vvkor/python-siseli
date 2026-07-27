"""Exception hierarchy for the Siseli SDK."""

from __future__ import annotations


class SiseliError(Exception):
    """Base exception for all Siseli SDK errors."""


class AuthenticationError(SiseliError):
    """Raised when authentication fails.

    Attributes:
        http_status: HTTP status code returned by the server, or *None* when
            the failure occurred before a response was received.
        api_message: Short error message extracted from the API response body
            (e.g. the ``message`` or ``error`` field), or *None* when
            unavailable.  Never contains passwords, tokens, or other secrets.
    """

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        api_message: str | None = None,
    ) -> None:
        self.http_status = http_status
        self.api_message = api_message
        super().__init__(message)


class TokenExpiredError(AuthenticationError):
    """Raised when the access token has expired and cannot be refreshed."""


class ApiError(SiseliError):
    """Raised when the API returns a non-zero response code."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"API error {code}: {message}")


class NetworkError(SiseliError):
    """Raised on network-level failures (connection errors, timeouts, etc.)."""
