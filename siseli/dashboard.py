"""Dashboard summary helpers."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from .models.common import CountByValue, TimePoint
from .models.dashboard import DashboardSummary, LocationDistribution, StationRankEntry
from .station import _parse_time_point

RequestFunc = Callable[..., Awaitable[Any]]


async def fetch_dashboard_summary(request: RequestFunc) -> DashboardSummary:
    """Return top-level dashboard summary metrics."""
    data = await request("POST", "/apis/dashboard/summary/commons", json={})
    return DashboardSummary(
        daily_produced_quantity=data.get("dailyProducedQuantity"),
        total_produced_quantity=data.get("totalProducedQuantity"),
        total_power=data.get("totalPower"),
        saving_standard_carbon=data.get("savingStandardCarbon"),
        co2_emission_reduction=data.get("co2EmissionReduction"),
        so2_emission_reduction=data.get("so2EmissionReduction"),
        nox_emission_reduction=data.get("noxEmissionReduction"),
        devices_number=data.get("devicesNumber"),
        all_installed_capacity=data.get("allInstalledCapacity"),
        station_total_number=data.get("stationTotalNumber"),
        station_state_summary=[
            CountByValue(
                value=item.get("state"),
                count=item.get("count", 0),
                label=item.get("stateDict"),
                raw=item,
            )
            for item in data.get("stationStateSummary", [])
        ],
        raw=data,
    )


async def fetch_dashboard_daily_generation_time_rank(
    request: RequestFunc,
    *,
    asc: bool = False,
) -> list[StationRankEntry]:
    """Return dashboard station ranking by daily generation time."""
    data = await request(
        "POST",
        "/apis/dashboard/summary/station/dailyGenerationTimeRank",
        params={"asc": asc},
        json={},
    )
    return [
        StationRankEntry(name=item.get("name", ""), full_time=item.get("fullTime"), raw=item)
        for item in data
    ]


async def fetch_dashboard_station_distribution(
    request: RequestFunc,
    *,
    east_longitude: float | None = None,
    west_longitude: float | None = None,
    north_latitude: float | None = None,
    south_latitude: float | None = None,
    level: int | None = None,
) -> list[LocationDistribution]:
    """Return dashboard station distribution by location."""
    data = await request(
        "POST",
        "/apis/dashboard/summary/station/distribution/location",
        json={
            "eastLongitude": east_longitude,
            "westLongitude": west_longitude,
            "northLatitude": north_latitude,
            "southLatitude": south_latitude,
            "level": level,
        },
    )
    return [
        LocationDistribution(
            name=item.get("name"),
            longitude=item.get("longitude"),
            latitude=item.get("latitude"),
            raw=item,
        )
        for item in data
    ]


async def fetch_dashboard_monthly_generated_energy(
    request: RequestFunc,
) -> list[TimePoint]:
    """Return monthly generated energy points for the dashboard."""
    data = await request(
        "POST",
        "/apis/dashboard/summary/station/generatedEnergy/monthly",
        json={},
    )
    return [_parse_time_point(item) for item in data]
