"""Remote device configuration retrieval."""

from __future__ import annotations

import asyncio
import time
from typing import Any, Awaitable, Callable

from ._utils import parse_datetime
from .config_safety import (
    ConfigAccess,
    ConfigAccessDenied,
    ConfigRejected,
    ConfigWriteResult,
    ConfigWriteStatus,
    get_spec,
    related_keys,
    validate_config_value,
    values_equal,
)
from .exceptions import ApiError, NetworkError
from .models.config import ConfigBatchRead
from .models.state import AttributeMetadata
from .state import _parse_attribute_metadata

RequestFunc = Callable[..., Awaitable[Any]]


def _parse_config_map(raw: dict[str, dict] | None) -> dict[str, AttributeMetadata]:
    if not raw:
        return {}
    return {key: _parse_attribute_metadata(item, key) for key, item in raw.items()}



def _parse_batch_read(raw: dict) -> ConfigBatchRead:
    target_config = raw.get("targetConfig")
    return ConfigBatchRead(
        id=raw.get("id", ""),
        device_id=raw.get("deviceId", ""),
        scene=raw.get("scene"),
        request_keys=raw.get("requestKeys", []) or [],
        target_config=_parse_config_map(target_config if isinstance(target_config, dict) else None),
        gather_protocol_version_id=raw.get("gatherProtocolVersionId"),
        gather_protocol_version_code=raw.get("gatherProtocolVersionCode"),
        start_at=parse_datetime(raw.get("startAt")),
        end_at=parse_datetime(raw.get("endAt")),
        error=raw.get("error"),
        is_finished=raw.get("isFinished", False),
        created_at=parse_datetime(raw.get("createdAt")),
        raw=raw,
    )


async def fetch_device_config(
    request: RequestFunc,
    device_id: str,
    *,
    key: str = "",
    config_id: str = "",
) -> AttributeMetadata:
    """Read one remote device configuration value."""
    data = await request(
        "POST",
        "/apis/remote/device/config/read",
        params={"deviceId": device_id},
        json={"id": config_id, "key": key},
    )
    return _parse_attribute_metadata(data, key)


async def write_device_config(
    request: RequestFunc,
    device_id: str,
    *,
    key: str,
    value: Any,
    config_id: str = "",
) -> AttributeMetadata | None:
    """Write one remote device configuration value.

    A successful write returns ``data: null``, so ``None`` is a normal result.
    """
    data = await request(
        "POST",
        "/apis/remote/device/config/write",
        params={"deviceId": device_id},
        json={"id": config_id, "key": key, "value": value},
    )
    if not isinstance(data, dict):
        return None
    return _parse_attribute_metadata(data, key)


async def fetch_cached_device_configs(
    request: RequestFunc,
    device_id: str,
) -> dict[str, AttributeMetadata]:
    """Return cached remote configurations for a device."""
    data = await request(
        "POST",
        "/apis/remote/device/configs/cache/get",
        params={"deviceId": device_id},
    )
    return _parse_config_map(data)


async def fetch_device_configs(
    request: RequestFunc,
    device_id: str,
) -> ConfigBatchRead:
    """Start a batch remote configuration read."""
    data = await request(
        "POST",
        "/apis/remote/device/configs/read",
        params={"deviceId": device_id},
    )
    return _parse_batch_read(data)


async def fetch_device_config_batch_details(
    request: RequestFunc,
    batch_read_id: str,
) -> ConfigBatchRead:
    """Return status/details for a batch remote configuration read."""
    data = await request(
        "GET",
        "/apis/remote/device/configs/read/details",
        params={"batchReadId": batch_read_id},
    )
    return _parse_batch_read(data)


# Cloud codes where the DTU/inverter outcome is not known to the caller.
_UNKNOWN_OUTCOME_CODES = frozenset({71301, 70138})
MIN_WRITE_INTERVAL = 3.0
_locks: dict[str, asyncio.Lock] = {}
_last_write: dict[str, float] = {}


def config_value(meta: AttributeMetadata) -> Any:
    """Return the raw value from a configuration read response."""
    return meta.raw.get("value")


async def _read_value(request: RequestFunc, device_id: str, key: str) -> Any:
    return config_value(await fetch_device_config(request, device_id, key=key))


async def safe_write_device_config(
    request: RequestFunc,
    device_id: str,
    *,
    key: str,
    value: Any,
    access: ConfigAccess = ConfigAccess.SAFE,
    battery_nominal_voltage: int = 12,
    dry_run: bool = False,
    min_interval: float = MIN_WRITE_INTERVAL,
) -> ConfigWriteResult:
    """Validate, write once and verify a configuration value.

    The write is never retried. If the cloud times out or the response cannot
    be parsed, the outcome is checked by reading the key back; when that is
    inconclusive the result is ``UNKNOWN`` rather than success.
    """
    spec = get_spec(key)
    if spec.risk > access:
        raise ConfigAccessDenied(f"{key} requires access level {spec.risk.name.lower()}")

    lock = _locks.setdefault(device_id, asyncio.Lock())
    async with lock:
        # Fail closed: any read needed for safety checks must succeed.
        previous = await _read_value(request, device_id, key)
        related: dict[str, Any] = {}
        for other in related_keys(key):
            related[other] = await _read_value(request, device_id, other)

        wire = validate_config_value(
            key,
            value,
            access=access,
            battery_nominal_voltage=battery_nominal_voltage,
            related_values=related,
        )
        if dry_run:
            return ConfigWriteResult(
                key, ConfigWriteStatus.DRY_RUN, wire, previous=previous, current=previous
            )
        if values_equal(wire, previous):
            return ConfigWriteResult(
                key, ConfigWriteStatus.APPLIED, wire, previous=previous, current=previous,
                message="already set",
            )

        wait = min_interval - (time.monotonic() - _last_write.get(device_id, -1e9))
        if wait > 0:
            await asyncio.sleep(wait)
        error_code: int | None = None
        message = ""
        try:
            await write_device_config(request, device_id, key=key, value=wire)
        except ApiError as exc:
            if exc.code not in _UNKNOWN_OUTCOME_CODES:
                raise ConfigRejected(exc.code, exc.message) from exc
            error_code, message = exc.code, exc.message
        except NetworkError as exc:
            message = str(exc)
        finally:
            _last_write[device_id] = time.monotonic()

        try:
            current = await _read_value(request, device_id, key)
        except (ApiError, NetworkError):
            return ConfigWriteResult(
                key, ConfigWriteStatus.UNKNOWN, wire, previous=previous,
                error_code=error_code, message=message or "read-back failed",
            )
        if values_equal(wire, current):
            return ConfigWriteResult(
                key, ConfigWriteStatus.APPLIED, wire, previous=previous, current=current,
                error_code=error_code, message=message,
            )
        return ConfigWriteResult(
            key, ConfigWriteStatus.UNKNOWN, wire, previous=previous, current=current,
            error_code=error_code, message=message or "read-back mismatch",
        )
