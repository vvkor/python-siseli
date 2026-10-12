"""State, attribute, and energy-flow models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .common import LookupValue


def _numeric(value: Any) -> float | None:
    """Return finite numeric telemetry as a float, otherwise None."""
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    if number != number or number in (float("inf"), float("-inf")):
        return None
    return number


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
    """A group of related state attributes."""

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

    def to_sensor_data(self) -> dict[str, Any]:
        """Return stable, typed semantic telemetry fields for integrations.

        API-specific field names, unit conversions, and derived battery values
        belong here rather than in consumer integrations. Invalid numeric
        telemetry is represented as None. Power values reported in kW by this
        device are converted to W.
        """
        def value(api_key: str) -> Any:
            attribute = self.fields.get(api_key)
            return attribute.value if attribute is not None else None

        def number(api_key: str) -> float | None:
            return _numeric(value(api_key))

        voltage = number("batteryVoltage")
        charging = number("batteryChargingCurrent")
        discharging = number("batteryDischargeCurrent")
        current = (
            charging - discharging
            if charging is not None and discharging is not None
            else None
        )
        return {
            "battery_soc": number("batteryCapacity"),
            "battery_voltage": voltage,
            "battery_current": current,
            "battery_power": voltage * current if voltage is not None and current is not None else None,
            "pv_voltage": number("pvInputVoltage1"),
            "pv_current": number("pv1InputCurrentForBattery"),
            "pv_power": (number("generationPower") * 1000 if number("generationPower") is not None else None),
            "grid_voltage": number("gridVoltage"),
            "grid_frequency": number("gridFrequency"),
            "output_voltage": number("acOutputVoltage"),
            "output_frequency": number("acOutputFrequency"),
            "load_power": (number("acOutputActivePower") * 1000 if number("acOutputActivePower") is not None else None),
            "inverter_state": value("workingMode"),
        }


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
