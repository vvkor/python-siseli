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
        validate_config_value(
            "setBatteryCutOffVoltage",
            11,
            access=ConfigAccess.ADVANCED,
            battery_nominal_voltage=12,
        )


def test_enum_and_number_bounds():
    with pytest.raises(ConfigValidationError):
        validate_config_value("buzzerEnabled", "2")
    kw = {"access": ConfigAccess.CRITICAL, "battery_nominal_voltage": 12, "related_values": VOLTAGES}
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


def test_battery_scaled_key_requires_explicit_nominal_voltage():
    with pytest.raises(
        ConfigValidationError,
        match="battery nominal voltage must be specified explicitly for setBatteryCutOffVoltage",
    ):
        validate_config_value(
            "setBatteryCutOffVoltage",
            12,
            access=ConfigAccess.CRITICAL,
            related_values=VOLTAGES,
        )

    cloud = FakeCloud(VOLTAGES)
    with pytest.raises(ConfigValidationError, match="must be specified explicitly"):
        run(cloud, "setBatteryCutOffVoltage", 12, access=ConfigAccess.CRITICAL)
    assert cloud.writes == []


def test_non_battery_scaled_keys_need_no_nominal_voltage():
    assert validate_config_value("buzzerEnabled", True) == "1"
    assert validate_config_value(
        "setMaxChargingCurrent",
        60,
        access=ConfigAccess.CRITICAL,
    ) == "60"


def test_voltage_order_enforced():
    kw = {"access": ConfigAccess.CRITICAL, "battery_nominal_voltage": 12, "related_values": VOLTAGES}
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


@pytest.mark.parametrize("status", [400, 403, 404])
def test_http_4xx_is_rejected(status):
    cloud = FakeCloud(
        {"buzzerEnabled": "0"}, write_error=NetworkError("denied", http_status=status)
    )
    with pytest.raises(ConfigRejected):
        run(cloud, "buzzerEnabled", 1)


@pytest.mark.parametrize("status", [None, 408, 429, 500, 503])
def test_transient_network_error_is_unknown(status):
    cloud = FakeCloud(
        {"buzzerEnabled": "0"}, write_error=NetworkError("x", http_status=status)
    )
    assert run(cloud, "buzzerEnabled", 1).status is ConfigWriteStatus.UNKNOWN
    assert len(cloud.writes) == 1


def test_write_non_dict_response_is_loud():
    import asyncio

    from siseli.config import write_device_config
    from siseli.exceptions import SiseliError

    async def request(*args, **kwargs):
        return ["unexpected"]

    with pytest.raises(SiseliError):
        asyncio.run(write_device_config(request, "d", key="buzzerEnabled", value=1))

    async def ok(*args, **kwargs):
        return None

    assert asyncio.run(write_device_config(ok, "d", key="buzzerEnabled", value=1)) is None


class BlockingCloud(FakeCloud):
    def __init__(self, values):
        super().__init__(values)
        self.release = None
        self.started = []

    async def __call__(self, method, path, **kwargs):
        if path.endswith("config/write"):
            self.started.append(kwargs["json"]["value"])
            if self.release is not None and len(self.started) == 1:
                await self.release.wait()
        return await super().__call__(method, path, **kwargs)


def test_writes_serialized_per_device_but_not_across_devices():
    import asyncio

    async def scenario():
        cloud = BlockingCloud({"buzzerEnabled": "0"})
        cloud.release = asyncio.Event()
        other = BlockingCloud({"buzzerEnabled": "0"})
        kw = {"key": "buzzerEnabled", "min_interval": 0}
        first = asyncio.create_task(
            safe_write_device_config(cloud, "ser-dev-a", value=1, **kw)
        )
        while not cloud.started:
            await asyncio.sleep(0)
        second = asyncio.create_task(
            safe_write_device_config(cloud, "ser-dev-a", value=0, **kw)
        )
        third = await asyncio.wait_for(
            safe_write_device_config(other, "ser-dev-b", value=1, **kw), 1
        )
        for _ in range(20):
            await asyncio.sleep(0)
        assert third.applied
        assert cloud.started == ["1"]
        assert not second.done()
        cloud.release.set()
        await asyncio.gather(first, second)
        assert cloud.started == ["1", "0"]

    asyncio.run(scenario())


def test_min_interval_between_writes(monkeypatch):
    import asyncio

    from siseli import config

    now = [100.0]
    sleeps = []

    async def fake_sleep(delay):
        sleeps.append(delay)
        now[0] += delay

    monkeypatch.setattr(config, "_monotonic", lambda: now[0])
    monkeypatch.setattr(config, "_sleep", fake_sleep)
    monkeypatch.setitem(config._last_write, "interval-dev", 99.0)

    async def scenario():
        cloud = FakeCloud({"buzzerEnabled": "0"})
        kw = {"key": "buzzerEnabled", "min_interval": 3.0}
        await safe_write_device_config(cloud, "interval-dev", value=1, **kw)
        now[0] += 1.0
        await safe_write_device_config(cloud, "interval-dev", value=0, **kw)

    asyncio.run(scenario())
    assert sleeps == [pytest.approx(2.0), pytest.approx(2.0)]
    asyncio.run(scenario())
    config._last_write.pop("interval-dev", None)


def test_definite_rejection_raises():
    cloud = FakeCloud({"buzzerEnabled": "0"}, write_error=ApiError(20210, "no rights"))
    with pytest.raises(ConfigRejected):
        run(cloud, "buzzerEnabled", 1)


def test_fail_closed_when_related_read_fails():
    values = dict(VOLTAGES)
    del values["setBatteryRechargingVoltage"]
    cloud = FakeCloud(values)
    with pytest.raises(ApiError):
        run(
            cloud,
            "setBatteryCutOffVoltage",
            11.5,
            access=ConfigAccess.CRITICAL,
            battery_nominal_voltage=12,
        )
    assert cloud.writes == []


def test_voltage_write_sends_number():
    cloud = FakeCloud(VOLTAGES)
    result = run(
        cloud,
        "setBatteryFloatChargingVoltage",
        13.6,
        access=ConfigAccess.CRITICAL,
        battery_nominal_voltage=12,
    )
    assert result.applied
    assert cloud.writes == [("setBatteryFloatChargingVoltage", 13.6)]
