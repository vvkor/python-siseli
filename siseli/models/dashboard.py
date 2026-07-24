"""Dashboard models."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .common import CountByValue, TimePoint


@dataclass
class StationRankEntry:
    """Dashboard station ranking entry."""

    name: str
    full_time: float | int | None
    raw: dict = field(repr=False)


@dataclass
class DashboardSummary:
    """Dashboard summary counters."""

    daily_produced_quantity: float | int | None
    total_produced_quantity: float | int | None
    total_power: float | int | None
    saving_standard_carbon: float | int | None
    co2_emission_reduction: float | int | None
    so2_emission_reduction: float | int | None
    nox_emission_reduction: float | int | None
    devices_number: int | None
    all_installed_capacity: float | int | None
    station_total_number: int | None
    station_state_summary: list[CountByValue]
    raw: dict = field(repr=False)


@dataclass
class LocationDistribution:
    """Dashboard location distribution entry."""

    name: str | None
    longitude: float | None
    latitude: float | None
    raw: dict = field(repr=False)
