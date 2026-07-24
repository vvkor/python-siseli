"""Device-related models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class Device:
    """A Siseli device (inverter, battery, etc.)."""

    id: str
    name: str
    serial_number: str
    state: int
    is_online: bool
    device_sort_key: str
    station_id: str | None
    station_name: str | None
    station_timezone: str | None
    rated_power: float
    producing_power: float
    model: str | None
    software_version: str | None
    last_data_at: datetime | None
    last_online_at: datetime | None
    created_at: datetime | None
    raw: dict = field(repr=False)
