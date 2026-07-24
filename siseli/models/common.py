"""Common models shared by multiple Siseli API areas."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Generic, TypeVar

T = TypeVar("T")


@dataclass
class LookupValue:
    """One value from a lookup table or enum."""

    value: Any
    name: str
    locale_text: str | None
    raw: dict = field(repr=False)


@dataclass
class CountByValue:
    """Count grouped by a dictionary value."""

    value: Any
    count: int
    label: str | None
    raw: dict = field(repr=False)


@dataclass
class TimePoint:
    """One aggregated point in a time series."""

    time: datetime | None
    time_display: str
    value: Any
    is_real_value: bool | None
    raw: dict = field(repr=False)


@dataclass
class PagedResult(Generic[T]):
    """Generic paginated response wrapper."""

    page: int
    count: int
    total: int
    items: list[T]
    raw: dict = field(repr=False)
