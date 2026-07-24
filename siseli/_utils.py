"""Shared parsing helpers for Siseli API payloads."""

from __future__ import annotations

from datetime import datetime
from typing import Any


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def serialize_datetime(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return value.isoformat().replace("+00:00", "Z")


def extract_value(raw: Any) -> Any:
    if not isinstance(raw, dict):
        return raw
    for key in ("vd", "valueDisplay", "value"):
        if key in raw:
            return raw[key]
    return raw
