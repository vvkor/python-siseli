"""Remote configuration models."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from .state import AttributeMetadata


@dataclass
class ConfigBatchRead:
    """Batch configuration read request and its progress."""

    id: str
    device_id: str
    scene: int | None
    request_keys: list[str]
    target_config: dict[str, AttributeMetadata]
    gather_protocol_version_id: str | None
    gather_protocol_version_code: str | None
    start_at: datetime | None
    end_at: datetime | None
    error: Any
    is_finished: bool
    created_at: datetime | None
    raw: dict = field(repr=False)
