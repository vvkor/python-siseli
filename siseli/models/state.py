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

        def display(api_key: str) -> str | None:
            attribute = self.fields.get(api_key)
            text = attribute.value_display if attribute is not None else None
            return text.strip() or None if isinstance(text, str) else None

        def power_watts(api_key: str) -> float | None:
            # The API reports power as kW unless the unit is explicitly W.
            result = number(api_key)
            attribute = self.fields.get(api_key)
            if result is None or attribute is None:
                return result
            return result if attribute.unit == "W" else result * 1000

        voltage = number("batteryVoltage")
        charging = number("batteryChargingCurrent")
        discharging = number("batteryDischargeCurrent")
        current = (
            charging - discharging
            if charging is not None and discharging is not None
            else None
        )
        pv_power = power_watts("generationPower")
        load_power = power_watts("acOutputActivePower")
        battery_power = (
            voltage * current
            if voltage is not None and current is not None
            else None
        )
        return {
            "battery_soc": number("batteryCapacity"),
            "battery_voltage": voltage,
            "battery_current": current,
            "battery_power": battery_power,
            "pv_voltage": number("pvInputVoltage1"),
            "pv_current": number("pv1InputCurrentForBattery"),
            "pv_power": pv_power,
            "grid_voltage": number("gridVoltage"),
            "grid_frequency": number("gridFrequency"),
            "output_voltage": number("acOutputVoltage"),
            "output_frequency": number("acOutputFrequency"),
            "load_power": load_power,
            "inverter_state": value("workingMode"),
            "inverter_mode": display("workingMode"),
            "load_percent": number("outputLoadPercent"),
            "load_apparent_power": number("ratedApparentPower"),
            "heat_sink_temperature": number("inverterHeatSinkTemperature"),
            "bus_voltage": number("busVoltage"),
            "charging_status": display("chargingStatus"),
            "scc_charging_status": display("sccChargingStatus"),
            "ac_charging_status": display("acChargingStatus"),
            "mains_status": display("mainsStatus"),
            "load_status": display("loadStatus"),
            "charger_source_priority": display("chargerSourcePriority"),
            "output_source_priority": display("outputSourcePriority"),
            "battery_type": display("batteryType"),
        }

    def to_device_info(self) -> dict[str, str | None]:
        """Return identification fields suitable for a device registry entry."""
        def display(api_key: str) -> str | None:
            attribute = self.fields.get(api_key)
            text = attribute.value_display if attribute is not None else None
            return text.strip() or None if isinstance(text, str) else None

        return {
            "protocol": display("protocolId"),
            "machine_type": display("machineType"),
            "firmware_version": display("mainCpuFirmwareVersion"),
            "secondary_firmware_version": display("secondaryCpuFirmwareVersion"),
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
