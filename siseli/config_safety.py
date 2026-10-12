"""Allowlist, validation and result types for safe remote configuration writes.

Writes go through the cloud to the DTU and then to the inverter as real
protocol commands. The registry below is deliberately conservative: unknown
keys are rejected, numeric values are bounded, and risky keys require an
explicit access level.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, IntEnum
from typing import Any

from .exceptions import SiseliError


class ConfigAccess(IntEnum):
    """Highest risk tier a caller allows to be written."""

    READ_ONLY = 0
    SAFE = 1
    ADVANCED = 2
    CRITICAL = 3


class ConfigKind(str, Enum):
    ENUM = "enum"
    NUMBER = "number"


class ConfigWriteStatus(str, Enum):
    APPLIED = "applied"
    UNKNOWN = "unknown"
    DRY_RUN = "dry_run"


class ConfigError(SiseliError):
    """Base class for configuration write errors."""


class ConfigValidationError(ConfigError):
    """The requested key/value is not allowed or out of range."""


class ConfigAccessDenied(ConfigError):
    """The key requires a higher access level than the caller granted."""


class ConfigRejected(ConfigError):
    """The cloud rejected the write with a definite error."""

    def __init__(self, code: int, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"Configuration write rejected ({code}): {message}")


@dataclass(frozen=True)
class ConfigSpec:
    key: str
    name: str
    kind: ConfigKind
    risk: ConfigAccess
    options: Mapping[str, str] = field(default_factory=dict)
    unit: str = ""
    minimum: float | None = None
    maximum: float | None = None
    step: float | None = None
    # Voltage limits below are for a 12 V battery and scale with the bank.
    scales_with_battery: bool = False
    # The cloud expects numbers for voltages/times and strings for the rest.
    wire_as_string: bool = True


_ON_OFF = {"0": "Disable", "1": "Enable"}

CONFIG_SPECS: dict[str, ConfigSpec] = {
    spec.key: spec
    for spec in (
        ConfigSpec("buzzerEnabled", "Buzzer", ConfigKind.ENUM, ConfigAccess.SAFE, _ON_OFF),
        ConfigSpec("lcdBackLightControlSetting", "LCD backlight", ConfigKind.ENUM, ConfigAccess.SAFE, _ON_OFF),
        ConfigSpec("lcdReturnToDefaultPageSetting", "LCD return to default page", ConfigKind.ENUM, ConfigAccess.SAFE, _ON_OFF),
        ConfigSpec("faultCodeRecordSetting", "Fault code record", ConfigKind.ENUM, ConfigAccess.SAFE, _ON_OFF),
        ConfigSpec("alarmOnWhenPrimarySourceInterruptSetting", "Alarm on primary source interrupt", ConfigKind.ENUM, ConfigAccess.SAFE, _ON_OFF),
        ConfigSpec("overTemperatureRestartSetting", "Over temperature restart", ConfigKind.ENUM, ConfigAccess.ADVANCED, _ON_OFF),
        ConfigSpec("overLoadRestartSetting", "Overload restart", ConfigKind.ENUM, ConfigAccess.ADVANCED, _ON_OFF),
        ConfigSpec("overloadBypass", "Overload bypass", ConfigKind.ENUM, ConfigAccess.ADVANCED, _ON_OFF),
        ConfigSpec("powerSavingEnable", "Power saving", ConfigKind.ENUM, ConfigAccess.ADVANCED, _ON_OFF),
        ConfigSpec("setBatteryEqualizationEnable", "Battery equalization", ConfigKind.ENUM, ConfigAccess.ADVANCED, _ON_OFF),
        ConfigSpec(
            "settingDeviceOutputSourcePriority",
            "Output source priority",
            ConfigKind.ENUM,
            ConfigAccess.ADVANCED,
            {"0": "Utility first", "1": "Solar first", "2": "SBU"},
        ),
        ConfigSpec(
            "settingDeviceChargerPriority",
            "Charger source priority",
            ConfigKind.ENUM,
            ConfigAccess.ADVANCED,
            {"0": "Utility first", "1": "Solar first", "2": "Solar and utility", "3": "Solar only"},
        ),
        ConfigSpec(
            "settingDeviceGridWorkingRange",
            "Grid working range",
            ConfigKind.ENUM,
            ConfigAccess.ADVANCED,
            {"0": "Appliance", "1": "UPS"},
        ),
        ConfigSpec(
            "settingBatteryType",
            "Battery type",
            ConfigKind.ENUM,
            ConfigAccess.CRITICAL,
            {"0": "AGM", "1": "Flooded", "2": "User"},
        ),
        ConfigSpec(
            "setACOutputRatedVoltage",
            "AC output rated voltage",
            ConfigKind.ENUM,
            ConfigAccess.CRITICAL,
            {"220": "220 V", "230": "230 V", "240": "240 V"},
            unit="V",
        ),
        ConfigSpec(
            "settingInverterOutputRatingFrequency",
            "AC output rated frequency",
            ConfigKind.ENUM,
            ConfigAccess.CRITICAL,
            {"50": "50 Hz", "60": "60 Hz"},
            unit="Hz",
        ),
        ConfigSpec("setMaxChargingCurrent", "Max charging current", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="A", minimum=10, maximum=80, step=10),
        ConfigSpec("setUtilityMaxChargingCurrent", "Max utility charging current", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="A", minimum=10, maximum=80, step=10),
        ConfigSpec("setBatteryCutOffVoltage", "Battery cut-off voltage", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="V", minimum=10.0, maximum=12.5, step=0.1, scales_with_battery=True, wire_as_string=False),
        ConfigSpec("setBatteryRechargingVoltage", "Battery recharge voltage", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="V", minimum=11.0, maximum=13.0, step=0.1, scales_with_battery=True, wire_as_string=False),
        ConfigSpec("setBatteryRedischargingVoltage", "Battery re-discharge voltage", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="V", minimum=12.0, maximum=14.5, step=0.1, scales_with_battery=True, wire_as_string=False),
        ConfigSpec("setBatteryCVChargeVoltage", "Battery bulk (CV) voltage", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="V", minimum=13.5, maximum=15.0, step=0.1, scales_with_battery=True, wire_as_string=False),
        ConfigSpec("setBatteryFloatChargingVoltage", "Battery float voltage", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="V", minimum=13.0, maximum=14.6, step=0.1, scales_with_battery=True, wire_as_string=False),
        ConfigSpec("setBatteryEqualizationVoltage", "Equalization voltage", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="V", minimum=13.5, maximum=15.0, step=0.1, scales_with_battery=True, wire_as_string=False),
        ConfigSpec("setBatteryEqualizationTime", "Equalization time", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="min", minimum=5, maximum=900, step=5, wire_as_string=False),
        ConfigSpec("setBatteryEqualizationOverTime", "Equalization timeout", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="min", minimum=5, maximum=900, step=5, wire_as_string=False),
        ConfigSpec("setBatteryEqualizationPeriod", "Equalization period", ConfigKind.NUMBER, ConfigAccess.CRITICAL, unit="day", minimum=0, maximum=90, step=1, wire_as_string=False),
    )
}

# Keys seen in captures whose writes fail on the cloud side (code 70138).
UNSUPPORTED_WRITE_KEYS = frozenset({"activeOrInactiveBatteryEqualization"})

# (lower, higher): lower must stay strictly below higher.
_ORDER_RULES: tuple[tuple[str, str], ...] = (
    ("setBatteryCutOffVoltage", "setBatteryRechargingVoltage"),
    ("setBatteryRechargingVoltage", "setBatteryRedischargingVoltage"),
    ("setBatteryRedischargingVoltage", "setBatteryFloatChargingVoltage"),
)
# (lower, higher): lower must not exceed higher.
_ORDER_RULES_INCLUSIVE: tuple[tuple[str, str], ...] = (
    ("setBatteryFloatChargingVoltage", "setBatteryCVChargeVoltage"),
    ("setBatteryCVChargeVoltage", "setBatteryEqualizationVoltage"),
)

_BATTERY_NOMINALS = (12, 24, 48)


def related_keys(key: str) -> list[str]:
    """Config keys whose current value is needed to validate *key*."""
    related: list[str] = []
    for low, high in _ORDER_RULES + _ORDER_RULES_INCLUSIVE:
        if key == low:
            related.append(high)
        elif key == high:
            related.append(low)
    return related


def get_spec(key: str) -> ConfigSpec:
    spec = CONFIG_SPECS.get(key)
    if spec is None:
        raise ConfigValidationError(f"Configuration key is not writable: {key}")
    return spec


def ensure_access(spec: ConfigSpec, access: ConfigAccess) -> None:
    if spec.risk > access:
        raise ConfigAccessDenied(
            f"{spec.key} requires access level {spec.risk.name.lower()}, "
            f"allowed: {access.name.lower()}"
        )


def _bounds(spec: ConfigSpec, nominal: int) -> tuple[float, float]:
    factor = nominal / 12 if spec.scales_with_battery else 1
    return spec.minimum * factor, spec.maximum * factor  # type: ignore[operator]


def validate_config_value(
    key: str,
    value: Any,
    *,
    access: ConfigAccess = ConfigAccess.SAFE,
    battery_nominal_voltage: int | None = None,
    related_values: Mapping[str, Any] | None = None,
) -> Any:
    """Validate a write and return the value to put on the wire.

    Raises ``ConfigValidationError`` / ``ConfigAccessDenied`` when the
    request must not be sent.
    """
    if key in UNSUPPORTED_WRITE_KEYS:
        raise ConfigValidationError(f"Writing {key} is not supported by the cloud")
    spec = get_spec(key)
    ensure_access(spec, access)
    if battery_nominal_voltage is None and spec.scales_with_battery:
        raise ConfigValidationError(
            f"battery nominal voltage must be specified explicitly for {key}"
        )
    if (
        battery_nominal_voltage is not None
        and battery_nominal_voltage not in _BATTERY_NOMINALS
    ):
        raise ConfigValidationError(
            f"Unsupported battery nominal voltage: {battery_nominal_voltage}"
        )

    if spec.kind is ConfigKind.ENUM:
        text = _enum_text(value)
        if text not in spec.options:
            raise ConfigValidationError(
                f"{key}: {value!r} is not one of {sorted(spec.options)}"
            )
        return text

    number = _as_number(key, value)
    low, high = _bounds(spec, battery_nominal_voltage)
    if not low - 1e-9 <= number <= high + 1e-9:
        raise ConfigValidationError(f"{key}: {number} is outside {low:g}..{high:g} {spec.unit}")
    step = spec.step * (battery_nominal_voltage / 12 if spec.scales_with_battery else 1)
    steps = (number - low) / step
    if abs(steps - round(steps)) > 1e-6:
        raise ConfigValidationError(f"{key}: {number} does not match step {step:g}")
    if spec.step is not None and spec.step < 1:
        number = round(number, 1)
    _check_order(key, number, related_values or {})
    wire: Any = int(number) if float(number).is_integer() else number
    return str(wire) if spec.wire_as_string else wire


def _enum_text(value: Any) -> str:
    if isinstance(value, bool):
        return "1" if value else "0"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value).strip()


def _as_number(key: str, value: Any) -> float:
    if isinstance(value, bool):
        raise ConfigValidationError(f"{key}: boolean is not a number")
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ConfigValidationError(f"{key}: {value!r} is not a number") from exc
    if not math.isfinite(number):
        raise ConfigValidationError(f"{key}: value must be finite")
    return number


def _check_order(key: str, number: float, related: Mapping[str, Any]) -> None:
    for strict, rules in ((True, _ORDER_RULES), (False, _ORDER_RULES_INCLUSIVE)):
        for low, high in rules:
            if key not in (low, high):
                continue
            other_key = high if key == low else low
            if other_key not in related:
                raise ConfigValidationError(
                    f"{key}: current value of {other_key} is required for the safety check"
                )
            other = _as_number(other_key, related[other_key])
            lo, hi = (number, other) if key == low else (other, number)
            if (strict and lo >= hi) or (not strict and lo > hi):
                op = "<" if strict else "<="
                raise ConfigValidationError(
                    f"{low} must be {op} {high} (got {lo:g} and {hi:g})"
                )


def values_equal(expected: Any, actual: Any) -> bool:
    """Compare a written value with a read-back value."""
    if actual is None:
        return False
    try:
        return abs(float(expected) - float(actual)) < 1e-6
    except (TypeError, ValueError):
        return str(expected).strip().lower() == str(actual).strip().lower()


@dataclass(frozen=True)
class ConfigWriteResult:
    key: str
    status: ConfigWriteStatus
    requested: Any
    previous: Any = None
    current: Any = None
    error_code: int | None = None
    message: str = ""

    @property
    def applied(self) -> bool:
        return self.status is ConfigWriteStatus.APPLIED
