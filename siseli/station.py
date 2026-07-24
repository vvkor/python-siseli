"""Station retrieval and aggregation helpers."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from ._utils import parse_datetime, serialize_datetime
from .const import DEFAULT_PAGE_SIZE
from .models.common import PagedResult, TimePoint
from .models.station import Station, StationEnergyFlow, StationSummary, SummaryCategory, SummaryProperty
from .state import _parse_flow_node

RequestFunc = Callable[..., Awaitable[Any]]



def _parse_station(raw: dict) -> Station:
    return Station(
        id=raw.get("id", ""),
        name=raw.get("name", ""),
        timezone=raw.get("timezone"),
        country=raw.get("country"),
        province=raw.get("province"),
        city=raw.get("city"),
        area=raw.get("area"),
        address=raw.get("address"),
        longitude=raw.get("longitude"),
        latitude=raw.get("latitude"),
        station_type=raw.get("stationType"),
        connected_grid_type=raw.get("connectedGridType"),
        state=raw.get("state"),
        is_online=raw.get("isOnline"),
        installed_capacity=raw.get("installedCapacity"),
        total_power=raw.get("totalPower"),
        daily_produced_quantity=raw.get("dailyProducedQuantity"),
        total_produced_quantity=raw.get("totalProducedQuantity"),
        created_at=parse_datetime(raw.get("createdAt")),
        raw=raw,
    )



def _parse_time_point(raw: dict) -> TimePoint:
    return TimePoint(
        time=parse_datetime(raw.get("time")),
        time_display=raw.get("timeDisplay", ""),
        value=raw.get("value", raw.get("generatedEnergy")),
        is_real_value=raw.get("isRealValue"),
        raw=raw,
    )



def _parse_summary_category(raw: dict | None) -> SummaryCategory | None:
    if raw is None:
        return None
    return SummaryCategory(
        id=raw.get("id", ""),
        key=raw.get("key", ""),
        name=raw.get("name", ""),
        raw=raw,
    )



def _parse_station_summary(raw: dict) -> StationSummary:
    properties = [
        SummaryProperty(
            property=item.get("property", {}),
            time_points=[_parse_time_point(point) for point in item.get("timePoints", [])],
            has_real_time_points=item.get("hasRealTimePoints"),
            raw=item,
        )
        for item in raw.get("properties", [])
    ]
    return StationSummary(
        category=_parse_summary_category(raw.get("category")),
        properties=properties,
        has_real_time_points=raw.get("hasRealTimePoints", False),
        raw=raw,
    )


async def fetch_station_list(
    request: RequestFunc,
    *,
    page: int = 1,
    count: int = DEFAULT_PAGE_SIZE,
    name: str = "",
    connected_grid_type: str = "",
    state: str = "",
    station_type: str = "",
) -> PagedResult[Station]:
    """Return a page of stations."""
    data = await request(
        "POST",
        "/apis/station/list",
        json={
            "page": page,
            "count": count,
            "name": name,
            "connectedGridType": connected_grid_type,
            "state": state,
            "stationType": station_type,
        },
    )
    items = [_parse_station(item) for item in data.get("list", [])]
    return PagedResult(
        page=data.get("page", page),
        count=data.get("count", count),
        total=data.get("total", len(items)),
        items=items,
        raw=data,
    )


async def fetch_station_details(request: RequestFunc, station_id: str) -> Station:
    """Return station details."""
    data = await request("GET", "/apis/station/details", params={"stationId": station_id})
    return _parse_station(data)


async def fetch_station_energy_flow(
    request: RequestFunc,
    station_id: str,
    *,
    is_manual_refresh: bool = False,
) -> StationEnergyFlow:
    """Return current station energy-flow data."""
    data = await request(
        "GET",
        "/apis/station/energy/flow",
        params={"stationId": station_id, "isManualRefresh": is_manual_refresh},
    )
    return StationEnergyFlow(
        is_support_flow=data.get("isSupportFlow", False),
        time=parse_datetime(data.get("time")),
        pv_panel=_parse_flow_node(data.get("pvPanelFlow")),
        grid=_parse_flow_node(data.get("gridFlow")),
        battery=_parse_flow_node(data.get("batteryFlow")),
        load=_parse_flow_node(data.get("loadFlow")),
        generator=_parse_flow_node(data.get("generatorFlow")),
        ups=_parse_flow_node(data.get("upsFlow")),
        ct=_parse_flow_node(data.get("ctFlow")),
        raw=data,
    )


async def fetch_station_income(
    request: RequestFunc,
    station_id: str,
    aggregation: str,
    *,
    time: Any = None,
) -> list[TimePoint]:
    """Return aggregated station income points."""
    data = await request(
        "POST",
        f"/apis/stationOverView/income/{aggregation}",
        params={"stationId": station_id},
        json={"time": serialize_datetime(time)},
    )
    return [_parse_time_point(item) for item in data]


async def fetch_station_state_summary(
    request: RequestFunc,
    station_id: str,
    summary_category_key: str,
    aggregation: str,
    *,
    time: Any = None,
) -> StationSummary:
    """Return aggregated station summary metrics."""
    data = await request(
        "POST",
        f"/apis/stationOverView/stateAttributeSummary/category/{aggregation}",
        params={"stationId": station_id, "summaryCategoryKey": summary_category_key},
        json={"time": serialize_datetime(time)},
    )
    return _parse_station_summary(data)
