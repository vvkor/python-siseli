"""State, attribute, and energy-flow models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .common import LookupValue


@dataclass
class StateAttribute:
    """A single telemetry attribute."""

    key: str
    unit: str
    value: Any
    value_display: str
    name_display: str
    is_hidden: bool | None


@dataclass
class AttributeMetadata:
    """Metadata describing a state or configuration attribute."""

    key: str
    name: str
    name_display: str
    unit: str
    value_type: int | None
    category: int | None
    operation_mode: int | None
    is_hidden: bool | None
    is_config_attribute: bool | None
    is_writable_config_attribute: bool | None
    is_readable_config_attribute: bool | None
    is_state_attribute: bool | None
    is_event_attribute: bool | None
    enum_values: list[LookupValue]
    raw: dict = field(repr=False)


@dataclass
class AttributeGroup:
    """A group of related device attributes."""

    id: str
    key: str
    category: int | None
    name: str
    description: str
    attributes: list[AttributeMetadata]
    raw: dict = field(repr=False)


@dataclass
class AttributeGroupSet:
    """Grouped attribute metadata for a device."""

    gather_protocol_version_id: str
    groups: list[AttributeGroup]
    raw: dict = field(repr=False)


@dataclass
class DeviceState:
    """Latest telemetry snapshot for a device."""

    time: datetime | None
    fields: dict[str, StateAttribute]
    raw: dict = field(repr=False)

    def get(self, key: str) -> StateAttribute | None:
        """Return an attribute by its key, or *None* if not present."""
        return self.fields.get(key)


@dataclass
class FlowNode:
    """One node of the energy-flow diagram (PV panel, grid, battery, load…)."""

    key: str
    locale_title: str
    value: StateAttribute | None
    flow_direction: int | None
    is_light: bool | None
    is_enabled: bool
    extra_values: list[StateAttribute]
    raw: dict = field(repr=False)


@dataclass
class EnergyFlow:
    """Energy-flow snapshot for a device."""

    device_state: DeviceState
    pv_panel: FlowNode | None
    grid: FlowNode | None
    battery: FlowNode | None
    load: FlowNode | None
    generator: FlowNode | None
    ups: FlowNode | None
    ct: FlowNode | None
    raw: dict = field(repr=False)
