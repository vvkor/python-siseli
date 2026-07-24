"""Historical telemetry retrieval."""

from __future__ import annotations

from typing import Any, Awaitable, Callable, Iterable

from ._utils import extract_value, parse_datetime, serialize_datetime
from .const import DEFAULT_PAGE_SIZE
from .models.history import HistoryRecord, HistorySeries

RequestFunc = Callable[..., Awaitable[Any]]


def _build_history_records(
    time_series: list[str],
    fields: dict[str, list[Any]],
) -> list[HistoryRecord]:
    records: list[HistoryRecord] = []
    for index, timestamp in enumerate(time_series):
        values = {
            key: extract_value(series[index]) if index < len(series) else None
            for key, series in fields.items()
        }
        records.append(
            HistoryRecord(
                time=parse_datetime(timestamp),
                values=values,
                raw={
                    "time": timestamp,
                    "values": {
                        key: series[index] if index < len(series) else None
                        for key, series in fields.items()
                    },
                },
            )
        )
    return records


async def fetch_attribute_history(
    request: RequestFunc,
    device_id: str,
    keys: Iterable[str],
    *,
    from_time: Any = None,
    to_time: Any = None,
    page: int = 1,
    count: int = DEFAULT_PAGE_SIZE,
    order_by_time_asc: bool = True,
) -> HistorySeries:
    """Return history for selected attribute keys."""
    data = await request(
        "POST",
        "/apis/deviceState/simple/attribute/keys/history/v1",
        json={
            "deviceId": device_id,
            "keys": list(keys),
            "fromTime": serialize_datetime(from_time),
            "toTime": serialize_datetime(to_time),
            "page": page,
            "count": count,
            "orderByTimeAsc": order_by_time_asc,
        },
    )
    payload = data.get("payload", {})
    raw_fields = payload.get("fields", {})
    time_series = payload.get("timeSeries", [])
    normalized_fields = {
        key: [extract_value(value) for value in values]
        for key, values in raw_fields.items()
    }
    return HistorySeries(
        page=data.get("page", page),
        count=data.get("count", count),
        total=data.get("total", len(time_series)),
        time_series=[parse_datetime(value) for value in time_series],
        fields=normalized_fields,
        formatters=payload.get("formatters", {}),
        records=_build_history_records(time_series, raw_fields),
        raw=data,
    )


async def fetch_state_history(
    request: RequestFunc,
    device_id: str,
    *,
    from_time: Any = None,
    to_time: Any = None,
    page: int = 1,
    count: int = DEFAULT_PAGE_SIZE,
    order_by_time_asc: bool = False,
) -> HistorySeries:
    """Return paginated historical device state records."""
    data = await request(
        "POST",
        "/apis/deviceState/simple/attribute/record/list/v1",
        json={
            "deviceId": device_id,
            "fromTime": serialize_datetime(from_time),
            "toTime": serialize_datetime(to_time),
            "page": page,
            "count": count,
            "orderByTimeAsc": order_by_time_asc,
        },
    )
    payload = data.get("payload", {})
    raw_fields = payload.get("fields", {})
    time_series = payload.get("timeSeries", [])
    normalized_fields = {
        key: [extract_value(value) for value in values]
        for key, values in raw_fields.items()
    }
    return HistorySeries(
        page=data.get("page", page),
        count=data.get("count", count),
        total=data.get("total", len(time_series)),
        time_series=[parse_datetime(value) for value in time_series],
        fields=normalized_fields,
        formatters={},
        records=_build_history_records(time_series, raw_fields),
        raw=data,
    )
