"""Station-related models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .common import TimePoint
from .state import FlowNode


@dataclass
class Station:
    """A Siseli station."""

    id: str
    name: str
    timezone: str | None
    country: str | None
    province: str | None
    city: str | None
    area: str | None
    address: str | None
    longitude: float | None
    latitude: float | None
    station_type: int | None
    connected_grid_type: int | None
    state: int | None
    is_online: bool | None
    installed_capacity: float | None
    total_power: float | None
    daily_produced_quantity: float | None
    total_produced_quantity: float | None
    created_at: datetime | None
    raw: dict = field(repr=False)


@dataclass
class StationEnergyFlow:
    """Energy-flow snapshot for a station."""

    is_support_flow: bool
    time: datetime | None
    pv_panel: FlowNode | None
    grid: FlowNode | None
    battery: FlowNode | None
    load: FlowNode | None
    generator: FlowNode | None
    ups: FlowNode | None
    ct: FlowNode | None
    raw: dict = field(repr=False)


@dataclass
class SummaryCategory:
    """Summary category metadata."""

    id: str
    key: str
    name: str
    raw: dict = field(repr=False)


@dataclass
class SummaryProperty:
    """One property within an aggregated summary."""

    property: dict[str, Any]
    time_points: list[TimePoint]
    has_real_time_points: bool | None
    raw: dict = field(repr=False)


@dataclass
class StationSummary:
    """Aggregated station summary series."""

    category: SummaryCategory | None
    properties: list[SummaryProperty]
    has_real_time_points: bool
    raw: dict = field(repr=False)
