"""Historical telemetry models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class HistoryRecord:
    """One timestamped historical record."""

    time: datetime | None
    values: dict[str, Any]
    raw: dict = field(repr=False)


@dataclass
class HistorySeries:
    """Historical attribute values for a device."""

    page: int
    count: int
    total: int
    time_series: list[datetime | None]
    fields: dict[str, list[Any]]
    formatters: dict[str, Any]
    records: list[HistoryRecord]
    raw: dict = field(repr=False)

    def get_series(self, key: str) -> list[Any]:
        """Return all values for one key, preserving API order."""
        return self.fields.get(key, [])
