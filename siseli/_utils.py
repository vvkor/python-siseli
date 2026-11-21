"""Shared parsing helpers for Siseli API payloads."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = value.replace("Z", "+00:00")
    if len(text) == 4 and text.isdigit():
        text = f"{text}-01-01"
    elif len(text) == 7 and text[4] == "-":
        text = f"{text}-01"
    return ensure_aware(datetime.fromisoformat(text))


def ensure_aware(value: datetime) -> datetime:
    """Treat naive timestamps from the API as UTC so they compare safely."""
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


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


def as_dict(value: Any) -> dict:
    """Return *value* if it is a dict, else an empty dict (handles JSON null)."""
    return value if isinstance(value, dict) else {}


def as_list(value: Any) -> list:
    """Return *value* if it is a list, else an empty list (handles JSON null)."""
    return value if isinstance(value, list) else []


_SEGMENT_RE = re.compile(r"^[A-Za-z0-9_-]+$")


def validate_path_segment(value: str, label: str) -> str:
    """Reject values that could alter the URL path when interpolated."""
    if not isinstance(value, str) or not _SEGMENT_RE.match(value):
        raise ValueError(f"invalid {label}: {value!r}")
    return value
