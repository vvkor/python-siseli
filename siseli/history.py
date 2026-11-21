"""Historical telemetry retrieval."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Iterable
from typing import Any

from ._utils import as_dict, as_list, extract_value, parse_datetime, serialize_datetime
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


def _build_series(
    data: Any, page: int, count: int, *, keep_formatters: bool
) -> HistorySeries:
    data = as_dict(data)
    payload = as_dict(data.get("payload"))
    raw_fields = {
        key: as_list(values) for key, values in as_dict(payload.get("fields")).items()
    }
    time_series = as_list(payload.get("timeSeries"))
    return HistorySeries(
        page=data.get("page", page),
        count=data.get("count", count),
        total=data.get("total", len(time_series)),
        time_series=[parse_datetime(value) for value in time_series],
        fields={
            key: [extract_value(value) for value in values]
            for key, values in raw_fields.items()
        },
        formatters=as_dict(payload.get("formatters")) if keep_formatters else {},
        records=_build_history_records(time_series, raw_fields),
        raw=data,
    )


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
    return _build_series(data, page, count, keep_formatters=True)


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
    return _build_series(data, page, count, keep_formatters=False)
