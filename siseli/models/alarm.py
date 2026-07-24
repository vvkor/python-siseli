"""Alarm-related models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Alarm:
    """One alarm entry."""

    id: str
    device_id: str | None
    device_serial_number: str | None
    device_name: str | None
    station_id: str | None
    station_name: str | None
    level: int | None
    state: int | None
    category: int | None
    title: str | None
    content: str | None
    created_at: datetime | None
    processed_at: datetime | None
    raw: dict = field(repr=False)


@dataclass
class AlarmReport:
    """Alarm report/export entry."""

    id: str
    remark: str | None
    report_from_time: datetime | None
    report_to_time: datetime | None
    progress: int | None
    state: int | None
    download_resid: str | None
    created_at: datetime | None
    raw: dict = field(repr=False)
