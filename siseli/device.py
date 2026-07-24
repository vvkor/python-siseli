"""Device discovery and details."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable

from .models.device import Device

RequestFunc = Callable[..., Awaitable[Any]]


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_device(raw: dict) -> Device:
    return Device(
        id=raw["id"],
        name=raw.get("name", ""),
        serial_number=raw.get("serialNumber", ""),
        state=raw.get("state", 0),
        is_online=raw.get("isOnline", False),
        device_sort_key=raw.get("deviceSortKey", ""),
        station_id=raw.get("stationId"),
        station_name=raw.get("stationName"),
        station_timezone=raw.get("stationTimezone"),
        rated_power=raw.get("ratedPower", 0.0),
        producing_power=raw.get("producingPower", 0.0),
        model=raw.get("model"),
        software_version=raw.get("softwareVersion"),
        last_data_at=_dt(raw.get("lastDataAt")),
        last_online_at=_dt(raw.get("lastOnlineAt")),
        created_at=_dt(raw.get("createdAt")),
        raw=raw,
    )


async def fetch_device_list(
    request: RequestFunc,
    *,
    page: int = 1,
    count: int = 20,
    name: str = "",
    serial_number: str = "",
    station_id: str = "",
    state: str = "",
) -> tuple[list[Device], int]:
    """Return a page of devices and the total count.

    :param request: Authenticated request callable from :class:`SiseliClient`.
    :param page: 1-based page number.
    :param count: Page size.
    :param name: Optional name filter (substring match).
    :param serial_number: Optional serial number filter.
    :param station_id: Optional station filter.
    :param state: Optional state filter.
    :returns: ``(devices, total)`` tuple.
    """
    data = await request(
        "POST",
        "/apis/device/list",
        json={
            "page": page,
            "count": count,
            "name": name,
            "serialNumber": serial_number,
            "stationId": station_id,
            "state": state,
            "fieldNames": [],
            "exportType": 0,
            "applyModeCategory": 1,
        },
    )
    devices = [_parse_device(d) for d in data.get("list", [])]
    total: int = data.get("total", len(devices))
    return devices, total


async def fetch_device_details(request: RequestFunc, device_id: str) -> Device:
    """Return full details for a single device.

    :param request: Authenticated request callable from :class:`SiseliClient`.
    :param device_id: The device ID.
    """
    data = await request("GET", "/apis/device/details", params={"deviceId": device_id})
    return _parse_device(data)
