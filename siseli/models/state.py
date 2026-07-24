"""State and energy-flow models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


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
class DeviceState:
    """Latest telemetry snapshot for a device."""

    time: datetime
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
