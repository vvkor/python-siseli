"""Tests for safe remote configuration writes."""

from __future__ import annotations

import pytest

from siseli.config import safe_write_device_config
from siseli.config_safety import (
    ConfigAccess,
    ConfigAccessDenied,
    ConfigRejected,
    ConfigValidationError,
    ConfigWriteStatus,
    validate_config_value,
)
from siseli.exceptions import ApiError, NetworkError


class FakeCloud:
    """Minimal request function emulating config read/write."""

    def __init__(self, values, *, write_error=None, apply_on_error=False):
        self.values = dict(values)
        self.write_error = write_error
        self.apply_on_error = apply_on_error
        self.writes = []

    async def __call__(self, method, path, **kwargs):
        body = kwargs.get("json", {})
        if path.endswith("config/read"):
            key = body["key"]
            if key not in self.values:
                raise ApiError(71301, "Remote dtu response timeout")
            return {"key": key, "value": self.values[key]}
        self.writes.append((body["key"], body["value"]))
        if self.write_error:
            if self.apply_on_error:
                self.values[body["key"]] = body["value"]
            raise self.write_error
        self.values[body["key"]] = body["value"]
        return None


VOLTAGES = {
    "setBatteryCutOffVoltage": 12,
    "setBatteryRechargingVoltage": 12.3,
    "setBatteryRedischargingVoltage": 13.3,
    "setBatteryCVChargeVoltage": 14.2,
    "setBatteryFloatChargingVoltage": 13.5,
    "setBatteryEqualizationVoltage": 14.6,
}


def run(cloud, key, value, **kwargs):
    import asyncio

    kwargs.setdefault("min_interval", 0)
    return asyncio.run(
        safe_write_device_config(
            cloud, f"dev-{id(cloud)}", key=key, value=value, **kwargs
        )
    )


def test_unknown_key_rejected():
    with pytest.raises(ConfigValidationError):
        validate_config_value("somethingElse", "1")


def test_unsupported_key_rejected():
    with pytest.raises(ConfigValidationError):
        validate_config_value("activeOrInactiveBatteryEqualization", "1", access=ConfigAccess.CRITICAL)


def test_access_levels():
    assert validate_config_value("buzzerEnabled", True) == "1"
    with pytest.raises(ConfigAccessDenied):
        validate_config_value("settingDeviceOutputSourcePriority", "1")
    assert validate_config_value("settingDeviceOutputSourcePriority", 1, access=ConfigAccess.ADVANCED) == "1"
    with pytest.raises(ConfigAccessDenied):
        validate_config_value("setBatteryCutOffVoltage", 11, access=ConfigAccess.ADVANCED)


def test_enum_and_number_bounds():
    with pytest.raises(ConfigValidationError):
        validate_config_value("buzzerEnabled", "2")
    kw = {"access": ConfigAccess.CRITICAL, "related_values": VOLTAGES}
    with pytest.raises(ConfigValidationError):
        validate_config_value("setBatteryCVChargeVoltage", 16, **kw)
    with pytest.raises(ConfigValidationError):
        validate_config_value("setBatteryCVChargeVoltage", float("nan"), **kw)
    with pytest.raises(ConfigValidationError):
        validate_config_value("setMaxChargingCurrent", 85, **kw)
    assert validate_config_value("setBatteryCVChargeVoltage", 14.4, **kw) == 14.4
    assert validate_config_value("setMaxChargingCurrent", 60, **kw) == "60"
    related24 = {k: v * 2 for k, v in VOLTAGES.items()}
    assert validate_config_value(
        "setBatteryCVChargeVoltage", 28.4, battery_nominal_voltage=24,
        access=ConfigAccess.CRITICAL, related_values=related24,
    ) == 28.4


def test_voltage_order_enforced():
    kw = {"access": ConfigAccess.CRITICAL, "related_values": VOLTAGES}
    with pytest.raises(ConfigValidationError):
        validate_config_value("setBatteryRechargingVoltage", 13.4, **kw)
    with pytest.raises(ConfigValidationError):
        validate_config_value("setBatteryRedischargingVoltage", 13.6, **kw)
    with pytest.raises(ConfigValidationError):
        validate_config_value("setBatteryFloatChargingVoltage", 14.5, **kw)
    with pytest.raises(ConfigValidationError):
        validate_config_value("setBatteryCVChargeVoltage", 14.2, access=ConfigAccess.CRITICAL)


def test_dry_run_does_not_write():
    cloud = FakeCloud({"buzzerEnabled": "0"})
    result = run(cloud, "buzzerEnabled", 1, dry_run=True)
    assert result.status is ConfigWriteStatus.DRY_RUN
    assert cloud.writes == []


def test_write_applied_with_readback():
    cloud = FakeCloud({"buzzerEnabled": "0"})
    result = run(cloud, "buzzerEnabled", 1)
    assert result.applied and result.previous == "0" and result.current == "1"
    assert cloud.writes == [("buzzerEnabled", "1")]


def test_same_value_skips_write():
    cloud = FakeCloud({"buzzerEnabled": "1"})
    assert run(cloud, "buzzerEnabled", 1).applied
    assert cloud.writes == []


def test_timeout_applied_after_readback_no_retry():
    cloud = FakeCloud({"buzzerEnabled": "0"}, write_error=ApiError(71301, "timeout"), apply_on_error=True)
    result = run(cloud, "buzzerEnabled", 1)
    assert result.applied and result.error_code == 71301
    assert len(cloud.writes) == 1


def test_timeout_without_apply_is_unknown():
    cloud = FakeCloud({"buzzerEnabled": "0"}, write_error=ApiError(70138, "parse"))
    result = run(cloud, "buzzerEnabled", 1)
    assert result.status is ConfigWriteStatus.UNKNOWN
    assert len(cloud.writes) == 1


def test_network_error_is_unknown_or_applied():
    cloud = FakeCloud({"buzzerEnabled": "0"}, write_error=NetworkError("boom"))
    assert run(cloud, "buzzerEnabled", 1).status is ConfigWriteStatus.UNKNOWN


def test_definite_rejection_raises():
    cloud = FakeCloud({"buzzerEnabled": "0"}, write_error=ApiError(20210, "no rights"))
    with pytest.raises(ConfigRejected):
        run(cloud, "buzzerEnabled", 1)


def test_fail_closed_when_related_read_fails():
    values = dict(VOLTAGES)
    del values["setBatteryRechargingVoltage"]
    cloud = FakeCloud(values)
    with pytest.raises(ApiError):
        run(cloud, "setBatteryCutOffVoltage", 11.5, access=ConfigAccess.CRITICAL)
    assert cloud.writes == []


def test_voltage_write_sends_number():
    cloud = FakeCloud(VOLTAGES)
    result = run(cloud, "setBatteryFloatChargingVoltage", 13.6, access=ConfigAccess.CRITICAL)
    assert result.applied
    assert cloud.writes == [("setBatteryFloatChargingVoltage", 13.6)]
