"""Lookup dictionary helpers."""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from .models.common import LookupValue
from .models.dictionary import DictionaryData

RequestFunc = Callable[..., Awaitable[Any]]



def _parse_lookup_values(values: list[dict] | None) -> list[LookupValue]:
    if not values:
        return []
    return [
        LookupValue(
            value=item.get("value"),
            name=item.get("name", item.get("text", item.get("localeText", ""))),
            locale_text=item.get("localeText"),
            raw=item,
        )
        for item in values
    ]


async def fetch_dictionary(request: RequestFunc, name: str) -> DictionaryData:
    """Return one dictionary dataset by name."""
    data = await request("GET", f"/apis/dictionary/data/{name}")
    metadata = {key: item for key, item in data.items() if not isinstance(item, list)}
    values = {
        key: _parse_lookup_values(item)
        for key, item in data.items()
        if isinstance(item, list)
    }
    return DictionaryData(name=name, values=values, raw=data, metadata=metadata)
