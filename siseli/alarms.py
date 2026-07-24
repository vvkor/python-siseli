"""Alarm retrieval helpers."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from ._utils import parse_datetime, serialize_datetime
from .const import DEFAULT_PAGE_SIZE
from .models.alarm import Alarm, AlarmReport
from .models.common import PagedResult

RequestFunc = Callable[..., Awaitable[Any]]



def _parse_alarm(raw: dict) -> Alarm:
    return Alarm(
        id=raw.get("id", ""),
        device_id=raw.get("deviceId"),
        device_serial_number=raw.get("deviceSerialNumber"),
        device_name=raw.get("deviceName"),
        station_id=raw.get("stationId"),
        station_name=raw.get("stationName"),
        level=raw.get("level"),
        state=raw.get("state"),
        category=raw.get("category"),
        title=raw.get("title") or raw.get("name") or raw.get("alarmName"),
        content=raw.get("content") or raw.get("message") or raw.get("remark"),
        created_at=parse_datetime(raw.get("createdAt")),
        processed_at=parse_datetime(raw.get("processedAt")),
        raw=raw,
    )



def _parse_alarm_report(raw: dict) -> AlarmReport:
    return AlarmReport(
        id=raw.get("id", ""),
        remark=raw.get("remark"),
        report_from_time=parse_datetime(raw.get("reportFromTime")),
        report_to_time=parse_datetime(raw.get("reportToTime") or raw.get("reportToFime")),
        progress=raw.get("progress"),
        state=raw.get("state"),
        download_resid=raw.get("downloadResid"),
        created_at=parse_datetime(raw.get("createdAt")),
        raw=raw,
    )


async def fetch_latest_alarm(
    request: RequestFunc,
    *,
    certificate_dtu_id: str = "",
    device_serial_number: str = "",
    page: int = 1,
    count: int = 1,
) -> Alarm | None:
    """Return the latest alarm matching filters."""
    data = await request(
        "POST",
        "/apis/alarm/getLatestAlarm",
        json={
            "certificateDtuID": certificate_dtu_id,
            "deviceSerialNumber": device_serial_number,
            "page": page,
            "count": count,
        },
    )
    if not data:
        return None
    return _parse_alarm(data)


async def fetch_alarm_list(
    request: RequestFunc,
    *,
    page: int = 1,
    count: int = DEFAULT_PAGE_SIZE,
    certificate_dtu_id: str = "",
    device_serial_number: str = "",
    from_time: Any = None,
    to_time: Any = None,
    is_processed: int | None = None,
    level: int | None = None,
    order_by_created_time_desc: bool = True,
) -> PagedResult[Alarm]:
    """Return paginated alarm history."""
    data = await request(
        "POST",
        "/apis/alarm/query/list",
        json={
            "page": page,
            "count": count,
            "certificateDtuID": certificate_dtu_id,
            "deviceSerialNumber": device_serial_number,
            "fromTime": serialize_datetime(from_time),
            "toTime": serialize_datetime(to_time),
            "isProcessed": is_processed,
            "level": level,
            "orderByCreatedTimeDesc": order_by_created_time_desc,
        },
    )
    items = [_parse_alarm(item) for item in data.get("list", [])]
    return PagedResult(
        page=data.get("page", page),
        count=data.get("count", count),
        total=data.get("total", len(items)),
        items=items,
        raw=data,
    )


async def fetch_alarm_report_headers(request: RequestFunc) -> list[dict[str, Any]]:
    """Return alarm report column definitions."""
    return await request("GET", "/apis/alarm/report/alarmList/headers")


async def fetch_alarm_report_details(request: RequestFunc, record_id: str) -> dict[str, Any]:
    """Return details for one alarm report record."""
    return await request(
        "GET",
        "/apis/alarm/report/record/details",
        params={"id": record_id},
    )


async def fetch_alarm_reports(
    request: RequestFunc,
    *,
    page: int = 1,
    count: int = DEFAULT_PAGE_SIZE,
    dtu_id: str = "",
    state: int | None = None,
    created_from_time: Any = None,
    created_to_time: Any = None,
    order_by_created_at_asc: bool = False,
) -> PagedResult[AlarmReport]:
    """Return alarm report/export history."""
    data = await request(
        "POST",
        "/apis/alarm/report/record/list",
        json={
            "page": page,
            "count": count,
            "dtuID": dtu_id,
            "state": state,
            "createdFromTime": serialize_datetime(created_from_time),
            "createdToTime": serialize_datetime(created_to_time),
            "orderByCreatedAtAsc": order_by_created_at_asc,
        },
    )
    items = [_parse_alarm_report(item) for item in data.get("list", [])]
    return PagedResult(
        page=data.get("page", page),
        count=data.get("count", count),
        total=data.get("total", len(items)),
        items=items,
        raw=data,
    )
