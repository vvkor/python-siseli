"""Null-safety, history parsing, path validation, timezone and unit handling."""

from __future__ import annotations

from datetime import UTC, datetime
from zoneinfo import ZoneInfo

import pytest

from siseli import _utils
from siseli.auth import Auth, _mask_account
from siseli.dashboard import fetch_dashboard_summary
from siseli.device import fetch_device_list
from siseli.dictionary import fetch_dictionary
from siseli.history import fetch_attribute_history, fetch_state_history
from siseli.models.state import DeviceState, StateAttribute
from siseli.overview import _time_payload, fetch_device_state_summary
from siseli.state import (
    fetch_device_attribute_groups,
    fetch_device_attributes,
    fetch_device_state,
    fetch_energy_flow,
)
from siseli.station import (
    fetch_station_income,
    fetch_station_list,
    fetch_station_state_summary,
)


def returning(value):
    async def request(method, path, **kwargs):
        return value

    return request


# ---------------------------------------------------------------------------
# _utils
# ---------------------------------------------------------------------------


def test_parse_datetime_is_always_timezone_aware():
    assert _utils.parse_datetime("2026-01-02T03:04:05").tzinfo is UTC
    assert _utils.parse_datetime("2026-01-02T03:04:05Z").tzinfo is not None
    assert _utils.parse_datetime("2026-01-02T03:04:05+02:00").utcoffset().total_seconds() == 7200
    assert _utils.parse_datetime("2026") == datetime(2026, 1, 1, tzinfo=UTC)
    assert _utils.parse_datetime("2026-03") == datetime(2026, 3, 1, tzinfo=UTC)
    assert _utils.parse_datetime(None) is None
    assert _utils.parse_datetime("") is None


def test_as_dict_and_as_list_tolerate_null():
    assert _utils.as_dict(None) == {}
    assert _utils.as_dict([1]) == {}
    assert _utils.as_dict({"a": 1}) == {"a": 1}
    assert _utils.as_list(None) == []
    assert _utils.as_list({}) == []
    assert _utils.as_list([1]) == [1]


@pytest.mark.parametrize("bad", ["", "../x", "a/b", "a?b", "a b", "a#b", "..", None])
def test_validate_path_segment_rejects_unsafe_values(bad):
    with pytest.raises(ValueError):
        _utils.validate_path_segment(bad, "thing")


def test_validate_path_segment_accepts_plain_names():
    assert _utils.validate_path_segment("daily", "x") == "daily"
    assert _utils.validate_path_segment("device_Batch-Upgrade", "x") == "device_Batch-Upgrade"


def test_extract_value_prefers_vd_then_display_then_value():
    assert _utils.extract_value({"vd": 1, "value": 2}) == 1
    assert _utils.extract_value({"valueDisplay": "x", "value": 2}) == "x"
    assert _utils.extract_value({"value": 2}) == 2
    assert _utils.extract_value(5) == 5


# ---------------------------------------------------------------------------
# Null / malformed payloads must not crash the parsers
# ---------------------------------------------------------------------------


async def test_device_list_handles_null_payloads():
    assert await fetch_device_list(returning(None)) == ([], 0)
    assert await fetch_device_list(returning({"list": None})) == ([], 0)


async def test_station_list_handles_null_list():
    result = await fetch_station_list(returning({"list": None}))
    assert result.items == [] and result.total == 0


async def test_device_state_handles_null_fields():
    state = await fetch_device_state(returning({"time": None, "fields": None}), "d")
    assert state.fields == {} and state.time is None
    assert (await fetch_device_state(returning(None), "d")).fields == {}


async def test_attribute_metadata_handles_null_enum_values():
    attrs = await fetch_device_attributes(
        returning([{"key": "k", "enumValues": None}]), "d"
    )
    assert attrs[0].enum_values == []
    assert await fetch_device_attributes(returning(None), "d") == []


async def test_attribute_groups_handle_nulls():
    groups = await fetch_device_attribute_groups(
        returning({"attributesGroups": [{"id": "g", "attributes": None}]}), "d"
    )
    assert groups.groups[0].attributes == []
    empty = await fetch_device_attribute_groups(returning(None), "d")
    assert empty.groups == []


async def test_energy_flow_handles_null_sections():
    flow = await fetch_energy_flow(
        returning(
            {
                "deviceAttributeState": None,
                "batteryFlow": {"key": "b", "value": None, "extraValues": None},
            }
        ),
        "d",
    )
    assert flow.device_state.fields == {}
    assert flow.battery is not None and flow.battery.value is None
    assert flow.battery.extra_values == []
    assert flow.grid is None


async def test_state_attribute_display_does_not_say_none():
    state = await fetch_device_state(
        returning({"fields": {"a": {"value": None}, "b": {"value": 3}}}), "d"
    )
    assert state.get("a").value_display == ""
    assert state.get("b").value_display == "3"


async def test_dashboard_and_summaries_handle_null():
    summary = await fetch_dashboard_summary(returning({"stationStateSummary": None}))
    assert summary.station_state_summary == []
    assert (await fetch_dashboard_summary(returning(None))).station_state_summary == []
    stats = await fetch_device_state_summary(returning(None), "d", "total")
    assert stats.properties == []


async def test_dictionary_handles_null_payload():
    result = await fetch_dictionary(returning(None), "units")
    assert result.values == {}


# ---------------------------------------------------------------------------
# History parsing (shared by both endpoints)
# ---------------------------------------------------------------------------

HISTORY = {
    "page": 2,
    "count": 5,
    "total": 12,
    "payload": {
        "timeSeries": ["2026-01-01T00:00:00Z", "2026-01-01T00:05:00Z"],
        "fields": {
            "gridVoltage": [{"vd": "230.1"}, {"vd": "229.8"}],
            "short": [{"vd": 1}],
        },
        "formatters": {"gridVoltage": {"unit": "V"}},
    },
}


async def test_attribute_history_parses_series_records_and_formatters():
    series = await fetch_attribute_history(returning(HISTORY), "d", ["gridVoltage"])
    assert (series.page, series.count, series.total) == (2, 5, 12)
    assert series.fields["gridVoltage"] == ["230.1", "229.8"]
    assert series.formatters == {"gridVoltage": {"unit": "V"}}
    assert series.time_series[0] == datetime(2026, 1, 1, tzinfo=UTC)
    assert series.records[1].values == {"gridVoltage": "229.8", "short": None}


async def test_state_history_drops_formatters():
    series = await fetch_state_history(returning(HISTORY), "d")
    assert series.formatters == {}
    assert len(series.records) == 2


async def test_history_request_body_serializes_times_and_keys():
    captured = {}

    async def request(method, path, **kwargs):
        captured.update(kwargs["json"])
        return None

    await fetch_attribute_history(
        request, "d", iter(["a", "b"]),
        from_time=datetime(2026, 1, 1, tzinfo=UTC), to_time="2026-01-02",
    )
    assert captured["keys"] == ["a", "b"]
    assert captured["fromTime"] == "2026-01-01T00:00:00Z"
    assert captured["toTime"] == "2026-01-02"


@pytest.mark.parametrize("payload", [None, {}, {"payload": None}, {"payload": {"fields": None}}])
async def test_history_handles_empty_or_null_payloads(payload):
    series = await fetch_state_history(returning(payload), "d")
    assert series.records == [] and series.time_series == [] and series.fields == {}


# ---------------------------------------------------------------------------
# URL path validation
# ---------------------------------------------------------------------------


async def test_station_aggregation_is_validated_before_any_request():
    async def request(*args, **kwargs):  # pragma: no cover - must not be reached
        raise AssertionError("request must not be sent")

    with pytest.raises(ValueError):
        await fetch_station_income(request, "s", "../../admin")
    with pytest.raises(ValueError):
        await fetch_station_state_summary(request, "s", "cat", "daily/../x")


async def test_dictionary_name_is_validated_before_any_request():
    async def request(*args, **kwargs):  # pragma: no cover
        raise AssertionError("request must not be sent")

    with pytest.raises(ValueError):
        await fetch_dictionary(request, "../secrets")


async def test_overview_rejects_unknown_aggregation():
    with pytest.raises(ValueError):
        await fetch_device_state_summary(returning({}), "d", "hourly")


# ---------------------------------------------------------------------------
# Timezone handling for "now"
# ---------------------------------------------------------------------------


def test_time_payload_uses_client_timezone(monkeypatch):
    import siseli.overview as overview

    class FixedDatetime(datetime):
        @classmethod
        def now(cls, tz=None):
            # 2026-03-31 23:30 UTC
            base = datetime(2026, 3, 31, 23, 30, tzinfo=UTC)
            return base.astimezone(tz) if tz else base

    monkeypatch.setattr(overview, "datetime", FixedDatetime)
    assert _time_payload("daily", None, "UTC") == {"time": "2026-03-31"}
    assert _time_payload("daily", None, "Asia/Tokyo") == {"time": "2026-04-01"}
    assert _time_payload("monthly", None, "Asia/Tokyo") == {"time": "2026-04"}
    assert _time_payload("yearly", None, "UTC") == {"time": "2026"}


def test_time_payload_falls_back_for_unknown_timezone():
    assert set(_time_payload("daily", None, "Not/AZone")) == {"time"}


def test_time_payload_explicit_values_win():
    assert _time_payload("daily", "2025-12-31", "Asia/Tokyo") == {"time": "2025-12-31"}
    moment = datetime(2025, 5, 6, 7, 8, tzinfo=ZoneInfo("UTC"))
    assert _time_payload("monthly", moment, "Asia/Tokyo") == {"time": "2025-05"}


async def test_client_passes_its_timezone_to_summaries():
    seen = {}

    async def request(method, path, **kwargs):
        seen.update(kwargs["json"])
        return {}

    await fetch_device_state_summary(request, "d", "daily", tz="Pacific/Kiritimati")
    expected = datetime.now(ZoneInfo("Pacific/Kiritimati")).strftime("%Y-%m-%d")
    assert seen["time"] == expected


# ---------------------------------------------------------------------------
# Power units
# ---------------------------------------------------------------------------


def _state(**fields) -> DeviceState:
    return DeviceState(
        time=None,
        fields={
            key: StateAttribute(
                key=key, unit=unit, value=value, value_display=str(value),
                name_display=key, is_hidden=False,
            )
            for key, (value, unit) in fields.items()
        },
        raw={},
    )


@pytest.mark.parametrize(
    "unit,expected",
    [("W", 500.0), ("w", 500.0), ("kW", 500_000.0), ("", 500_000.0), ("VA", None), ("MW", None)],
)
def test_power_unit_handling(unit, expected):
    data = _state(generationPower=(500, unit)).to_sensor_data()
    assert data["pv_power"] == expected


def test_rated_apparent_power_is_exposed_under_honest_name():
    data = _state(ratedApparentPower=(5000, "VA")).to_sensor_data()
    assert data["rated_apparent_power"] == 5000
    assert data["load_apparent_power"] == 5000  # deprecated alias


# ---------------------------------------------------------------------------
# Auth hygiene
# ---------------------------------------------------------------------------


def test_mask_account_hides_local_part():
    assert _mask_account("user@example.com") == "u***@example.com"
    assert _mask_account("plainlogin") == "p***"
    assert _mask_account("") == "***"
    assert "user" not in _mask_account("user@example.com").replace("u***", "")


async def test_login_logs_do_not_contain_account(caplog):
    import json

    import httpx

    class Http:
        async def post(self, url, **kwargs):
            return httpx.Response(
                401, content=json.dumps({"error": "bad"}).encode(),
                headers={"content-type": "application/json"},
                request=httpx.Request("POST", "https://x"),
            )

    caplog.set_level("DEBUG", logger="siseli.auth")
    from siseli.exceptions import AuthenticationError

    with pytest.raises(AuthenticationError):
        await Auth("secret.person@example.com", "pw").login(Http())
    assert "secret.person" not in caplog.text


def test_naive_expiry_does_not_break_is_authenticated():
    from siseli.models.auth import TokenInfo

    auth = Auth("a@b.c", "pw")
    auth._token_info = TokenInfo(
        access_token="t", refresh_token="r",
        access_token_expires_at=_utils.parse_datetime("2999-01-01T00:00:00"),
        refresh_token_expires_at=None, auth_id="", account="", user_id="",
    )
    assert auth.is_authenticated()
    auth._token_info.access_token_expires_at = _utils.parse_datetime("2000-01-01T00:00:00")
    assert not auth.is_authenticated()


def test_token_expiring_within_margin_counts_as_expired():
    from datetime import timedelta

    from siseli.models.auth import TokenInfo

    auth = Auth("a@b.c", "pw")
    auth._token_info = TokenInfo(
        access_token="t", refresh_token="r",
        access_token_expires_at=datetime.now(UTC) + timedelta(seconds=5),
        refresh_token_expires_at=None, auth_id="", account="", user_id="",
    )
    assert not auth.is_authenticated()
    auth.invalidate()
    assert auth.token_info is None
