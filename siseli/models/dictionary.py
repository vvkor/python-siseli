"""Dictionary and metadata models."""

from __future__ import annotations

from dataclasses import dataclass, field

from .common import LookupValue


@dataclass
class DictionaryData:
    """One dictionary dataset returned by the API."""

    name: str
    values: dict[str, list[LookupValue]]
    raw: dict = field(repr=False)
