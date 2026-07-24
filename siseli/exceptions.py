"""Exception hierarchy for the Siseli SDK."""

from __future__ import annotations


class SiseliError(Exception):
    """Base exception for all Siseli SDK errors."""


class AuthenticationError(SiseliError):
    """Raised when authentication fails."""


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
