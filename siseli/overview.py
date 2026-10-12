"""Device and owner overview (energy statistics) helpers."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable

from .models.common import TimePoint
from .models.station import StationSummary
from .station import _parse_station_summary, _parse_time_point

RequestFunc = Callable[..., Awaitable[Any]]

ENERGY_SUMMARY_CATEGORY = "pvInverterElectricityQuantityClass"
POWER_SUMMARY_CATEGORY = "pvInverterPowerClass"
AGGREGATIONS = ("daily", "monthly", "yearly", "total")

_TIME_FORMATS = {"daily": "%Y-%m-%d", "monthly": "%Y-%m", "yearly": "%Y"}


def _time_payload(aggregation: str, time: datetime | str | None) -> dict[str, str]:
    """Build the request body using the time format the web UI sends."""
    if aggregation not in AGGREGATIONS:
        raise ValueError(f"aggregation must be one of {AGGREGATIONS}, got {aggregation!r}")
    if isinstance(time, str):
        return {"time": time}
    moment = time or datetime.now().astimezone()
    pattern = _TIME_FORMATS.get(aggregation)
    return {"time": moment.strftime(pattern) if pattern else moment.isoformat()}


async def fetch_device_state_summary(
    request: RequestFunc,
    device_id: str,
    aggregation: str,
    *,
    summary_category_key: str = ENERGY_SUMMARY_CATEGORY,
    time: datetime | str | None = None,
) -> StationSummary:
    """Return aggregated device statistics (daily, monthly, yearly or total)."""
    data = await request(
        "POST",
        f"/apis/deviceOverView/stateAttributeSummary/category/{aggregation}",
        params={"deviceId": device_id, "summaryCategoryKey": summary_category_key},
        json=_time_payload(aggregation, time),
    )
    return _parse_station_summary(data)


async def fetch_owner_state_summary(
    request: RequestFunc,
    aggregation: str,
    *,
    summary_category_key: str = ENERGY_SUMMARY_CATEGORY,
    time: datetime | str | None = None,
) -> StationSummary:
    """Return aggregated statistics across all stations of the account."""
    data = await request(
        "POST",
        f"/apis/ownerOverView/station/stateAttributeSummary/category/{aggregation}",
        params={"summaryCategoryKey": summary_category_key},
        json=_time_payload(aggregation, time),
    )
    return _parse_station_summary(data)


async def fetch_device_generated_energy_daily(
    request: RequestFunc,
    device_id: str,
    *,
    time: datetime | str | None = None,
) -> list[TimePoint]:
    """Return half-hourly generated energy for one day."""
    data = await request(
        "POST",
        "/apis/deviceOverView/generatedEnergy/daily",
        params={"deviceId": device_id},
        json=_time_payload("daily", time),
    )
    return [_parse_time_point(item) for item in data]


async def fetch_device_power_class_daily_detail(
    request: RequestFunc,
    device_id: str,
    *,
    time: datetime | str | None = None,
) -> dict[str, Any]:
    """Return the raw per-day PV inverter power series (``timeSeries`` payload)."""
    return await request(
        "POST",
        "/apis/deviceOverView/pvInverterPowerClass/daily/detail",
        params={"deviceId": device_id},
        json=_time_payload("daily", time),
    )
