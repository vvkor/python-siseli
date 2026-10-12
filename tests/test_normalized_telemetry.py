"""Tests for semantic device telemetry normalization."""

from datetime import UTC, datetime

import pytest

from siseli.models.state import DeviceState, StateAttribute


def make_state(values: dict) -> DeviceState:
    fields = {
        key: StateAttribute(
            key=key,
            unit="",
            value=value,
            value_display=str(value),
            name_display=key,
            is_hidden=False,
        )
        for key, value in values.items()
    }
    return DeviceState(time=datetime.now(UTC), fields=fields, raw={})


def test_to_sensor_data_maps_fields_and_converts_power_units() -> None:
    result = make_state(
        {
            "batteryCapacity": 85,
            "batteryVoltage": 52.1,
            "batteryChargingCurrent": 10.5,
            "batteryDischargeCurrent": 0,
            "pvInputVoltage1": 380,
            "pv1InputCurrentForBattery": 3.2,
            "generationPower": 1.216,
            "gridVoltage": 230,
            "gridFrequency": 50,
            "acOutputVoltage": 230,
            "acOutputFrequency": 50,
            "acOutputActivePower": 0.420,
            "workingMode": "B",
        }
    ).to_sensor_data()

    assert result["battery_soc"] == pytest.approx(85)
    assert result["battery_current"] == pytest.approx(10.5)
    assert result["battery_power"] == pytest.approx(547.05)
    assert result["pv_power"] == pytest.approx(1216)
    assert result["load_power"] == pytest.approx(420)
    assert result["inverter_state"] == "B"
    assert "grid_power" not in result


def test_to_sensor_data_handles_discharge_and_invalid_values() -> None:
    result = make_state(
        {
            "batteryVoltage": 52.1,
            "batteryChargingCurrent": 0,
            "batteryDischargeCurrent": 4.2,
            "pvInputVoltage1": "--",
            "pv1InputCurrentForBattery": True,
            "generationPower": float("nan"),
            "acOutputActivePower": "not available",
            "workingMode": "B",
        }
    ).to_sensor_data()

    assert result["battery_current"] == pytest.approx(-4.2)
    assert result["battery_power"] == pytest.approx(-52.1 * 4.2)
    assert result["pv_voltage"] is None
    assert result["pv_current"] is None
    assert result["pv_power"] is None
    assert result["load_power"] is None
    assert result["inverter_state"] == "B"


def test_to_sensor_data_returns_none_when_derived_inputs_missing() -> None:
    result = make_state(
        {"batteryVoltage": 12.8, "batteryChargingCurrent": 1}
    ).to_sensor_data()
    assert result["battery_current"] is None
    assert result["battery_power"] is None
