"""Device state (latest telemetry) and energy-flow retrieval."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Awaitable, Callable

from .const import DEFAULT_DATA_SOURCE
from .models.state import DeviceState, EnergyFlow, FlowNode, StateAttribute

RequestFunc = Callable[..., Awaitable[Any]]


def _dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _parse_attribute(key: str, raw: dict) -> StateAttribute:
    return StateAttribute(
        key=raw.get("key", key),
        unit=raw.get("unit", ""),
        value=raw.get("value"),
        value_display=raw.get("valueDisplay", ""),
        name_display=raw.get("nameDisplay", ""),
        is_hidden=raw.get("isHidden"),
    )


def _parse_device_state(raw: dict) -> DeviceState:
    fields_raw: dict = raw.get("fields", {})
    fields = {key: _parse_attribute(key, attr) for key, attr in fields_raw.items()}
    return DeviceState(
        time=_dt(raw.get("time")),
        fields=fields,
        raw=raw,
    )


def _parse_flow_node(raw: dict | None) -> FlowNode | None:
    if raw is None:
        return None
    value_raw = raw.get("value")
    value = _parse_attribute(raw.get("key", ""), value_raw) if value_raw else None
    return FlowNode(
        key=raw.get("key", ""),
        locale_title=raw.get("localeTitle", ""),
        value=value,
        flow_direction=raw.get("flowDirection"),
        is_light=raw.get("isLight"),
        is_enabled=raw.get("isEnabled", True),
        raw=raw,
    )


async def fetch_device_state(
    request: RequestFunc,
    device_id: str,
    *,
    data_source: int = DEFAULT_DATA_SOURCE,
) -> DeviceState:
    """Return the latest telemetry snapshot for *device_id*.

    :param request: Authenticated request callable from :class:`SiseliClient`.
    :param device_id: The device ID.
    :param data_source: API ``dataSource`` parameter (default ``1``).
    """
    data = await request(
        "GET",
        "/apis/deviceState/simple/state/latest/v1",
        params={"deviceId": device_id, "dataSource": data_source},
    )
    return _parse_device_state(data)


async def fetch_energy_flow(
    request: RequestFunc,
    device_id: str,
    *,
    data_source: int = DEFAULT_DATA_SOURCE,
) -> EnergyFlow:
    """Return the current energy-flow diagram data for *device_id*.

    :param request: Authenticated request callable from :class:`SiseliClient`.
    :param device_id: The device ID.
    :param data_source: API ``dataSource`` parameter (default ``1``).
    """
    data = await request(
        "GET",
        "/apis/deviceState/simple/energy/flow/v1",
        params={"deviceId": device_id, "dataSource": data_source},
    )
    device_state = _parse_device_state(data.get("deviceAttributeState", {}))
    return EnergyFlow(
        device_state=device_state,
        pv_panel=_parse_flow_node(data.get("pvPanelFlow")),
        grid=_parse_flow_node(data.get("gridFlow")),
        battery=_parse_flow_node(data.get("batteryFlow")),
        load=_parse_flow_node(data.get("loadFlow")),
        generator=_parse_flow_node(data.get("generatorFlow")),
        ups=_parse_flow_node(data.get("upsFlow")),
        ct=_parse_flow_node(data.get("ctFlow")),
        raw=data,
    )
