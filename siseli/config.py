"""Remote device configuration retrieval."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from ._utils import parse_datetime
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
