"""Device state, metadata, and energy-flow retrieval."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from ._utils import parse_datetime
from .const import DEFAULT_DATA_SOURCE
from .models.common import LookupValue
from .models.state import (
    AttributeGroup,
    AttributeGroupSet,
    AttributeMetadata,
    DeviceState,
    EnergyFlow,
    FlowNode,
    StateAttribute,
)

RequestFunc = Callable[..., Awaitable[Any]]



def _parse_lookup_value(raw: dict) -> LookupValue:
    return LookupValue(
        value=raw.get("value"),
        name=raw.get("text", raw.get("name", raw.get("localeText", ""))),
        locale_text=raw.get("localeText"),
        raw=raw,
    )



def _parse_attribute(key: str, raw: dict) -> StateAttribute:
    return StateAttribute(
        key=raw.get("key", key),
        unit=raw.get("unit", ""),
        value=raw.get("value"),
        value_display=raw.get("valueDisplay", str(raw.get("value", ""))),
        name_display=raw.get("nameDisplay", raw.get("name", "")),
        is_hidden=raw.get("isHidden"),
    )



def _parse_attribute_metadata(raw: dict, key: str = "") -> AttributeMetadata:
    enum_values = [_parse_lookup_value(item) for item in raw.get("enumValues", [])]
    return AttributeMetadata(
        key=raw.get("key", key),
        name=raw.get("name", raw.get("nameDisplay", "")),
        name_display=raw.get("nameDisplay", raw.get("name", "")),
        unit=raw.get("unit", ""),
        value_type=raw.get("valueType"),
        category=raw.get("category"),
        operation_mode=raw.get("operationMode"),
        is_hidden=raw.get("isHidden"),
        is_config_attribute=raw.get("isConfigAttribute"),
        is_writable_config_attribute=raw.get("isWritableConfigAttribute"),
        is_readable_config_attribute=raw.get("isReadableConfigAttribute"),
        is_state_attribute=raw.get("isStateAttribute"),
        is_event_attribute=raw.get("isEventAttribute"),
        enum_values=enum_values,
        raw=raw,
    )



def _parse_attribute_group(raw: dict) -> AttributeGroup:
    return AttributeGroup(
        id=raw.get("id", ""),
        key=raw.get("key", ""),
        category=raw.get("category"),
        name=raw.get("name", ""),
        description=raw.get("description", ""),
        attributes=[_parse_attribute_metadata(item) for item in raw.get("attributes", [])],
        raw=raw,
    )



def _parse_device_state(raw: dict) -> DeviceState:
    fields_raw: dict = raw.get("fields", {})
    fields = {key: _parse_attribute(key, attr) for key, attr in fields_raw.items()}
    return DeviceState(
        time=parse_datetime(raw.get("time")),
        fields=fields,
        raw=raw,
    )



def _parse_flow_node(raw: dict | None) -> FlowNode | None:
    if raw is None:
        return None
    value_raw = raw.get("value")
    value = _parse_attribute(raw.get("key", ""), value_raw) if value_raw else None
    extra_values = [_parse_attribute(item.get("key", ""), item) for item in raw.get("extraValues", [])]
    return FlowNode(
        key=raw.get("key", ""),
        locale_title=raw.get("localeTitle", ""),
        value=value,
        flow_direction=raw.get("flowDirection"),
        is_light=raw.get("isLight"),
        is_enabled=raw.get("isEnabled", raw.get("enabled", True)),
        extra_values=extra_values,
        raw=raw,
    )


async def fetch_device_state(
    request: RequestFunc,
    device_id: str,
    *,
    data_source: int = DEFAULT_DATA_SOURCE,
) -> DeviceState:
    """Return the latest telemetry snapshot for *device_id*."""
    data = await request(
        "GET",
        "/apis/deviceState/simple/state/latest/v1",
        params={"deviceId": device_id, "dataSource": data_source},
    )
    return _parse_device_state(data)


async def fetch_device_attributes(
    request: RequestFunc,
    device_id: str,
    *,
    category: str = "",
    render_in: str = "",
) -> list[AttributeMetadata]:
    """Return attribute metadata for the device state screen."""
    data = await request(
        "GET",
        "/apis/deviceState/simple/gatherAttributes/v1",
        params={"deviceId": device_id, "category": category, "renderIn": render_in},
    )
    return [_parse_attribute_metadata(item) for item in data]


async def fetch_device_attribute_groups(
    request: RequestFunc,
    device_id: str,
    *,
    category: str = "",
    render_in: str = "",
) -> AttributeGroupSet:
    """Return grouped device attribute metadata."""
    data = await request(
        "GET",
        "/apis/device/query/attribute/group",
        params={"deviceId": device_id, "category": category, "renderIn": render_in},
    )
    return AttributeGroupSet(
        gather_protocol_version_id=data.get("gatherProtocolVersionId", ""),
        groups=[_parse_attribute_group(item) for item in data.get("attributesGroups", [])],
        raw=data,
    )


async def fetch_energy_flow(
    request: RequestFunc,
    device_id: str,
    *,
    data_source: int = DEFAULT_DATA_SOURCE,
) -> EnergyFlow:
    """Return the current energy-flow diagram data for *device_id*."""
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
