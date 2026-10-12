"""Tests for overview statistics and extended telemetry normalization."""

import asyncio
from datetime import UTC, datetime

import pytest

from siseli.models.state import DeviceState, StateAttribute
from siseli.overview import (
    fetch_device_generated_energy_daily,
    fetch_device_state_summary,
    fetch_owner_state_summary,
)


def make_request(response):
    calls = []

    async def request(method, path, **kwargs):
        calls.append((method, path, kwargs))
        return response

    return request, calls


def summary_payload() -> dict:
    def prop(key, points):
        return {
            "property": {"key": key, "unitI18n": {"en": "kWh"}, "unit": "kWh"},
            "timePoints": points,
            "hasRealTimePoints": True,
        }

    return {
        "category": {"id": "2", "key": "pvInverterElectricityQuantityClass", "name": "Energy"},
        "properties": [
            prop("pvGeneratedEnergy", [{"time": "2026", "timeDisplay": "2026", "value": 12.5, "isRealValue": True}]),
            prop("buyElectricityQuantity", []),
        ],
    }


def test_device_total_summary_request_and_totals() -> None:
    request, calls = make_request(summary_payload())
    summary = asyncio.run(
        fetch_device_state_summary(
            request, "dev1", "total", time=datetime(2026, 10, 12, 12, 0, tzinfo=UTC)
        )
    )

    method, path, kwargs = calls[0]
    assert method == "POST"
    assert path == "/apis/deviceOverView/stateAttributeSummary/category/total"
    assert kwargs["params"] == {
        "deviceId": "dev1",
        "summaryCategoryKey": "pvInverterElectricityQuantityClass",
    }
    assert kwargs["json"] == {"time": "2026-10-12T12:00:00+00:00"}
    assert summary.get("pvGeneratedEnergy").unit == "kWh"
    assert summary.to_totals() == {"pvGeneratedEnergy": 12.5, "buyElectricityQuantity": None}


@pytest.mark.parametrize(
    ("aggregation", "expected"),
    [("daily", "2026-10-12"), ("monthly", "2026-10"), ("yearly", "2026")],
)
def test_summary_time_format_per_aggregation(aggregation: str, expected: str) -> None:
    request, calls = make_request(summary_payload())
    asyncio.run(
        fetch_owner_state_summary(request, aggregation, time=datetime(2026, 10, 12, tzinfo=UTC))
    )
    assert calls[0][1].endswith(f"/ownerOverView/station/stateAttributeSummary/category/{aggregation}")
    assert calls[0][2]["json"] == {"time": expected}


def test_invalid_aggregation_rejected() -> None:
    request, _ = make_request(summary_payload())
    with pytest.raises(ValueError):
        asyncio.run(fetch_device_state_summary(request, "dev1", "weekly"))


def test_generated_energy_daily_points() -> None:
    request, calls = make_request(
        [{"time": "2026-10-12 10:00:00", "timeDisplay": "10:00", "value": 0.5, "isRealValue": True}]
    )
    points = asyncio.run(fetch_device_generated_energy_daily(request, "dev1", time="2026-10-12"))
    assert calls[0][2]["json"] == {"time": "2026-10-12"}
    assert points[0].value == 0.5
    assert points[0].time_display == "10:00"


def make_state(fields: dict) -> DeviceState:
    return DeviceState(
        time=None,
        fields={
            key: StateAttribute(key, unit, value, display, key, False)
            for key, (value, display, unit) in fields.items()
        },
        raw={},
    )


def test_extended_sensor_data_and_unit_aware_power() -> None:
    data = make_state(
        {
            "workingMode": ("L", "Line Mode", ""),
            "outputLoadPercent": (1, "1", "%"),
            "inverterHeatSinkTemperature": (49, "49", "°C"),
            "busVoltage": (419, "419", "V"),
            "ratedApparentPower": (23, "23", "VA"),
            "chargingStatus": ("1", "Charging On", ""),
            "acOutputActivePower": (350, "350", "W"),
            "generationPower": (0.5, "0.5", "kW"),
        }
    ).to_sensor_data()

    assert data["inverter_state"] == "L"
    assert data["inverter_mode"] == "Line Mode"
    assert data["load_percent"] == 1
    assert data["heat_sink_temperature"] == 49
    assert data["bus_voltage"] == 419
    assert data["load_apparent_power"] == 23
    assert data["charging_status"] == "Charging On"
    assert data["load_power"] == 350
    assert data["pv_power"] == 500
    assert data["mains_status"] is None


def test_device_info() -> None:
    info = make_state(
        {
            "protocolId": ("PI30", "PI30", ""),
            "machineType": ("x", "Off Grid", ""),
            "mainCpuFirmwareVersion": ("v", "00019.06", ""),
        }
    ).to_device_info()
    assert info["protocol"] == "PI30"
    assert info["machine_type"] == "Off Grid"
    assert info["firmware_version"] == "00019.06"
    assert info["secondary_firmware_version"] is None
