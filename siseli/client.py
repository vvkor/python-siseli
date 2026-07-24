"""SiseliClient — the main public entry point for the SDK."""

from __future__ import annotations

import time
from typing import Any

import httpx

from .auth import Auth
from .const import BASE_URL, DEFAULT_DATA_SOURCE, DEFAULT_PAGE_SIZE, DEFAULT_TIMEOUT
from .device import fetch_device_details, fetch_device_list
from .exceptions import ApiError, NetworkError
from .models.device import Device
from .models.state import DeviceState, EnergyFlow
from .state import fetch_device_state, fetch_energy_flow


class SiseliClient:
    """Async client for the Siseli Cloud API.

    Usage::

        async with SiseliClient("user@example.com", "secret") as client:
            devices = await client.get_devices()
            state = await client.get_device_state(devices[0].id)

    Alternatively, manage the lifecycle manually::

        client = SiseliClient("user@example.com", "secret")
        await client.authenticate()
        devices = await client.get_devices()
        await client.close()
    """

    def __init__(
        self,
        account: str,
        password: str,
        *,
        base_url: str = BASE_URL,
        timezone: str = "UTC",
        timeout: float = DEFAULT_TIMEOUT,
    ) -> None:
        self._auth = Auth(account, password)
        self._timezone = timezone
        self._http = httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def authenticate(self) -> None:
        """Authenticate and store the access token.

        Called automatically before the first request if not yet
        authenticated.  You may call this explicitly to verify credentials
        up front.

        Raises :exc:`~siseli.exceptions.AuthenticationError` on failure.
        """
        await self._auth.login(self._http)

    async def close(self) -> None:
        """Close the underlying HTTP connection pool."""
        await self._http.aclose()

    async def __aenter__(self) -> SiseliClient:
        await self.authenticate()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _ensure_authenticated(self) -> None:
        if not self._auth.is_authenticated():
            await self._auth.login(self._http)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Make an authenticated request and return the ``data`` field.

        Re-authenticates automatically when the access token has expired.

        Raises :exc:`~siseli.exceptions.ApiError` on non-zero response codes.
        Raises :exc:`~siseli.exceptions.NetworkError` on transport failures.
        """
        await self._ensure_authenticated()

        auth_headers = {
            "IOT-Token": self._auth.access_token,
            "IOT-Time-Zone": self._timezone,
        }

        try:
            response = await self._http.request(
                method, path, headers=auth_headers, **kwargs
            )
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise NetworkError(
                f"HTTP {exc.response.status_code} for {method} {path}"
            ) from exc
        except httpx.HTTPError as exc:
            raise NetworkError(f"Request failed for {method} {path}: {exc}") from exc

        body = response.json()
        if body.get("code") != 0:
            raise ApiError(body.get("code", -1), body.get("message", ""))

        return body.get("data")

    # ------------------------------------------------------------------
    # Device discovery
    # ------------------------------------------------------------------

    async def get_devices(
        self,
        *,
        page: int = 1,
        count: int = DEFAULT_PAGE_SIZE,
        name: str = "",
        serial_number: str = "",
        station_id: str = "",
        state: str = "",
    ) -> list[Device]:
        """Return a page of devices.

        :param page: 1-based page number (default ``1``).
        :param count: Number of results per page (default ``20``).
        :param name: Optional name filter.
        :param serial_number: Optional serial-number filter.
        :param station_id: Optional station filter.
        :param state: Optional state filter.
        """
        devices, _ = await fetch_device_list(
            self._request,
            page=page,
            count=count,
            name=name,
            serial_number=serial_number,
            station_id=station_id,
            state=state,
        )
        return devices

    async def get_all_devices(self) -> list[Device]:
        """Return **all** devices by fetching every page automatically."""
        all_devices: list[Device] = []
        page = 1
        while True:
            devices, total = await fetch_device_list(
                self._request,
                page=page,
                count=DEFAULT_PAGE_SIZE,
            )
            all_devices.extend(devices)
            if len(all_devices) >= total:
                break
            page += 1
        return all_devices

    async def get_device(self, device_id: str) -> Device:
        """Return full details for a single device.

        :param device_id: The device ID.
        """
        return await fetch_device_details(self._request, device_id)

    # ------------------------------------------------------------------
    # Telemetry
    # ------------------------------------------------------------------

    async def get_device_state(
        self,
        device_id: str,
        *,
        data_source: int = DEFAULT_DATA_SOURCE,
    ) -> DeviceState:
        """Return the latest telemetry snapshot for *device_id*.

        :param device_id: The device ID.
        :param data_source: API ``dataSource`` parameter (default ``1``).
        """
        return await fetch_device_state(
            self._request, device_id, data_source=data_source
        )

    async def get_energy_flow(
        self,
        device_id: str,
        *,
        data_source: int = DEFAULT_DATA_SOURCE,
    ) -> EnergyFlow:
        """Return the current energy-flow diagram data for *device_id*.

        :param device_id: The device ID.
        :param data_source: API ``dataSource`` parameter (default ``1``).
        """
        return await fetch_energy_flow(
            self._request, device_id, data_source=data_source
        )
