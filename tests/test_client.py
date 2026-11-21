"""Tests for SiseliClient: auth lifecycle, error mapping, retries, pagination."""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx

from siseli import SiseliClient
from siseli.exceptions import (
    ApiError,
    AuthenticationError,
    InvalidResponseError,
    NetworkError,
    RateLimitError,
)

BASE = "https://solar.siseli.com"


def login_body(token: str = "tok-1", expires: str | None = None) -> dict:
    return {
        "code": 0,
        "data": {
            "accessToken": token,
            "refreshToken": "ref",
            "accessTokenWillExpiredAt": expires,
            "refreshTokenWillExpiredAt": None,
            "authId": "a",
            "account": "user@example.com",
            "userId": "u",
        },
    }


def ok(data) -> httpx.Response:
    return httpx.Response(200, json={"code": 0, "data": data})


def make_client(**kwargs) -> SiseliClient:
    kwargs.setdefault("retry_backoff", 0)
    return SiseliClient("user@example.com", "secret", **kwargs)


@pytest.fixture(autouse=True)
def no_sleep(monkeypatch):
    async def instant(_delay):
        return None

    monkeypatch.setattr("siseli.client._sleep", instant)


@respx.mock
async def test_request_sends_token_and_timezone_headers():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.get(f"{BASE}/apis/device/details").mock(
        return_value=ok({"id": "d1", "name": "Inv"})
    )
    async with make_client(timezone="Europe/Warsaw") as client:
        device = await client.get_device("d1")
    assert device.id == "d1"
    sent = route.calls.last.request.headers
    assert sent["IOT-Token"] == "tok-1"
    assert sent["IOT-Time-Zone"] == "Europe/Warsaw"


@respx.mock
async def test_401_triggers_single_relogin_and_retry():
    login = respx.post(f"{BASE}/apis/login/account").mock(
        side_effect=[
            httpx.Response(200, json=login_body("tok-1")),
            httpx.Response(200, json=login_body("tok-2")),
        ]
    )
    route = respx.get(f"{BASE}/apis/device/details").mock(
        side_effect=[httpx.Response(401), ok({"id": "d1"})]
    )
    async with make_client() as client:
        assert (await client.get_device("d1")).id == "d1"
    assert login.call_count == 2
    assert route.calls[1].request.headers["IOT-Token"] == "tok-2"


@respx.mock
async def test_persistent_401_raises_authentication_error():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    respx.get(f"{BASE}/apis/device/details").respond(403)
    async with make_client() as client:
        with pytest.raises(AuthenticationError) as info:
            await client.get_device("d1")
    assert info.value.http_status == 403


@respx.mock
async def test_concurrent_requests_login_only_once():
    login = respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    respx.get(f"{BASE}/apis/device/details").mock(return_value=ok({"id": "d1"}))
    client = make_client()
    try:
        await asyncio.gather(*(client.get_device("d1") for _ in range(5)))
    finally:
        await client.close()
    assert login.call_count == 1


@respx.mock
async def test_expired_token_is_refreshed_before_request():
    login = respx.post(f"{BASE}/apis/login/account").mock(
        side_effect=[
            httpx.Response(200, json=login_body("old", "2000-01-01T00:00:00Z")),
            httpx.Response(200, json=login_body("new")),
        ]
    )
    route = respx.get(f"{BASE}/apis/device/details").mock(return_value=ok({"id": "d1"}))
    async with make_client() as client:
        await client.get_device("d1")
    assert login.call_count == 2
    assert route.calls.last.request.headers["IOT-Token"] == "new"


@respx.mock
async def test_429_is_retried_then_raises_rate_limit_error():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.get(f"{BASE}/apis/device/details").respond(
        429, headers={"Retry-After": "7"}
    )
    async with make_client(max_retries=2) as client:
        with pytest.raises(RateLimitError) as info:
            await client.get_device("d1")
    assert info.value.retry_after == 7
    assert info.value.http_status == 429
    assert isinstance(info.value, NetworkError)
    assert route.call_count == 3


@respx.mock
async def test_transient_5xx_recovers_after_retry():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.get(f"{BASE}/apis/device/details").mock(
        side_effect=[httpx.Response(503), ok({"id": "d1"})]
    )
    async with make_client() as client:
        assert (await client.get_device("d1")).id == "d1"
    assert route.call_count == 2


@respx.mock
async def test_connection_error_retried_then_network_error():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.get(f"{BASE}/apis/device/details").mock(
        side_effect=httpx.ConnectError("boom")
    )
    async with make_client(max_retries=1) as client:
        with pytest.raises(NetworkError):
            await client.get_device("d1")
    assert route.call_count == 2


@respx.mock
async def test_4xx_is_not_retried_and_keeps_status():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.get(f"{BASE}/apis/device/details").respond(404)
    async with make_client() as client:
        with pytest.raises(NetworkError) as info:
            await client.get_device("d1")
    assert info.value.http_status == 404
    assert route.call_count == 1


@respx.mock
async def test_config_write_is_never_retried_on_transport_failure():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.post(f"{BASE}/apis/remote/device/config/write").respond(503)
    async with make_client(max_retries=3) as client:
        with pytest.raises(NetworkError):
            await client.set_device_config("d1", key="buzzerEnabled", value="1")
    assert route.call_count == 1


@respx.mock
async def test_non_json_body_raises_invalid_response_error():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    respx.get(f"{BASE}/apis/device/details").respond(200, text="<html>oops</html>")
    async with make_client() as client:
        with pytest.raises(InvalidResponseError):
            await client.get_device("d1")


@respx.mock
async def test_non_object_json_raises_invalid_response_error():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    respx.get(f"{BASE}/apis/device/details").respond(200, json=[1, 2])
    async with make_client() as client:
        with pytest.raises(InvalidResponseError):
            await client.get_device("d1")


@respx.mock
async def test_api_error_code_maps_to_api_error():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    respx.get(f"{BASE}/apis/device/details").respond(
        json={"code": 20210, "message": "no rights", "data": None}
    )
    async with make_client() as client:
        with pytest.raises(ApiError) as info:
            await client.get_device("d1")
    assert info.value.code == 20210


@respx.mock
async def test_failed_login_in_aenter_closes_client(monkeypatch):
    respx.post(f"{BASE}/apis/login/account").respond(401, json={"error": "bad"})
    client = make_client()
    closed = []
    original = client.close

    async def tracking_close():
        closed.append(True)
        await original()

    monkeypatch.setattr(client, "close", tracking_close)
    with pytest.raises(AuthenticationError):
        async with client:
            pass
    assert closed == [True]


@respx.mock
async def test_login_with_non_json_or_missing_tokens_raises_invalid_response():
    route = respx.post(f"{BASE}/apis/login/account")
    for body in (httpx.Response(200, text="not json"),
                 httpx.Response(200, json={"code": 0, "data": {}})):
        route.mock(return_value=body)
        client = make_client()
        try:
            with pytest.raises(InvalidResponseError):
                await client.authenticate()
        finally:
            await client.close()


@respx.mock
async def test_injected_http_client_is_not_closed():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    http = httpx.AsyncClient(base_url=BASE)
    async with make_client(http_client=http):
        pass
    assert not http.is_closed
    await http.aclose()


@respx.mock
async def test_open_auth_option_signs_requests():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.get(f"{BASE}/apis/device/details").mock(return_value=ok({"id": "d"}))
    async with make_client(open_auth=True) as client:
        await client.get_device("d")
    headers = route.calls.last.request.headers
    assert headers["IOT-Open-Sign"] and headers["IOT-Open-Nonce"]
    assert "IOT-Open-Body-Hash" not in headers


# ---------------------------------------------------------------------------
# Pagination
# ---------------------------------------------------------------------------


def _device(n: int) -> dict:
    return {"id": f"d{n}", "name": f"Dev {n}"}


@respx.mock
async def test_get_all_devices_collects_all_pages():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    pages = {1: [_device(1), _device(2)], 2: [_device(3)]}

    def handler(request: httpx.Request) -> httpx.Response:
        import json

        page = json.loads(request.content)["page"]
        return ok({"list": pages.get(page, []), "total": 3})

    respx.post(f"{BASE}/apis/device/list").mock(side_effect=handler)
    async with make_client() as client:
        devices = await client.get_all_devices()
    assert [d.id for d in devices] == ["d1", "d2", "d3"]


@respx.mock
async def test_get_all_devices_stops_on_empty_page_even_if_total_is_larger():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.post(f"{BASE}/apis/device/list").mock(
        side_effect=[ok({"list": [_device(1)], "total": 99}), ok({"list": [], "total": 99})]
    )
    async with make_client() as client:
        devices = await client.get_all_devices()
    assert len(devices) == 1
    assert route.call_count == 2


@respx.mock
async def test_get_all_stations_stops_on_empty_page():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.post(f"{BASE}/apis/station/list").mock(
        side_effect=[
            ok({"list": [{"id": "s1", "name": "S"}], "total": 50}),
            ok({"list": None, "total": 50}),
        ]
    )
    async with make_client() as client:
        stations = await client.get_all_stations()
    assert [s.id for s in stations] == ["s1"]
    assert route.call_count == 2


@respx.mock
async def test_open_auth_does_not_sign_requests_to_other_hosts():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    other = respx.get("https://other.example.com/x").respond(200)
    http = httpx.AsyncClient(base_url=BASE)
    async with make_client(http_client=http, open_auth=True):
        await http.get("https://other.example.com/x")
    assert "IOT-Open-Sign" not in other.calls.last.request.headers
    await http.aclose()


@respx.mock
@pytest.mark.parametrize(
    "status,exc",
    [(429, RateLimitError), (503, NetworkError), (408, NetworkError), (401, AuthenticationError)],
)
async def test_login_status_mapping(status, exc):
    respx.post(f"{BASE}/apis/login/account").respond(status, json={"error": "x"})
    client = make_client()
    try:
        with pytest.raises(exc) as info:
            await client.authenticate()
    finally:
        await client.close()
    if status in (429, 503, 408):
        assert not isinstance(info.value, AuthenticationError)


@respx.mock
async def test_write_never_retried_even_via_explicit_flag_on_other_paths():
    respx.post(f"{BASE}/apis/login/account").respond(json=login_body())
    route = respx.post(f"{BASE}/apis/some/side/effect").respond(503)
    async with make_client(max_retries=3) as client:
        with pytest.raises(NetworkError):
            await client._request("POST", "/apis/some/side/effect", retry=False)
    assert route.call_count == 1
    assert "retry" not in route.calls.last.request.headers
