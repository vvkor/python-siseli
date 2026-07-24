"""Auth-related models."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass
class TokenInfo:
    """Tokens returned by a successful login."""

    access_token: str
    refresh_token: str
    access_token_expires_at: datetime
    refresh_token_expires_at: datetime
    auth_id: str
    account: str
    user_id: str
