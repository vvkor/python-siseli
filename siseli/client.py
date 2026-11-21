"""SiseliClient — the main public entry point for the SDK."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Iterable
from datetime import datetime
from typing import Any

import httpx

from .alarms import (
    fetch_alarm_list,
    fetch_alarm_report_details,
    fetch_alarm_report_headers,
    fetch_alarm_reports,
    fetch_latest_alarm,
)
from .auth import Auth
from .config import (
    fetch_cached_device_configs,
    fetch_device_config,
    fetch_device_config_batch_details,
    fetch_device_configs,
    safe_write_device_config,
    write_device_config,
)
from .config_safety import ConfigAccess, ConfigWriteResult
from .const import BASE_URL, DEFAULT_DATA_SOURCE, DEFAULT_PAGE_SIZE, DEFAULT_TIMEOUT
from .dashboard import (
    fetch_dashboard_daily_generation_time_rank,
    fetch_dashboard_monthly_generated_energy,
    fetch_dashboard_station_distribution,
    fetch_dashboard_summary,
)
from .device import fetch_device_details, fetch_device_list
from .dictionary import fetch_dictionary
from .exceptions import (
    ApiError,
    AuthenticationError,
    InvalidResponseError,
    NetworkError,
    RateLimitError,
)
from .history import fetch_attribute_history, fetch_state_history
from .models.alarm import Alarm, AlarmReport
from .models.common import PagedResult, TimePoint
from .models.config import ConfigBatchRead
from .models.dashboard import DashboardSummary, LocationDistribution, StationRankEntry
from .models.device import Device
from .models.dictionary import DictionaryData
from .models.history import HistorySeries
from .models.state import AttributeGroupSet, AttributeMetadata, DeviceState, EnergyFlow
from .models.station import Station, StationEnergyFlow, StationSummary
from .overview import (
    ENERGY_SUMMARY_CATEGORY,
    fetch_device_generated_energy_daily,
    fetch_device_power_class_daily_detail,
    fetch_device_state_summary,
    fetch_owner_state_summary,
)
from .state import (
    fetch_device_attribute_groups,
    fetch_device_attributes,
    fetch_device_state,
    fetch_energy_flow,
)
from .station import (
    fetch_station_details,
    fetch_station_energy_flow,
    fetch_station_income,
    fetch_station_list,
    fetch_station_state_summary,
)

_LOGGER = logging.getLogger(__name__)

# Requests with side effects must pass ``retry=False`` to ``_request`` so they
# are never re-sent after an ambiguous failure. This path list is a second
# line of defence for the one write endpoint the SDK currently has.
_NON_RETRYABLE_PATHS = ("/apis/remote/device/config/write",)
_sleep = asyncio.sleep
_RETRYABLE_STATUSES = frozenset({502, 503, 504})
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF = 0.5


def _retry_after(response: httpx.Response) -> float | None:
    try:
        return max(0.0, float(response.headers.get("Retry-After", "")))
    except ValueError:
        return None


class SiseliClient:
    """Async client for the Siseli Cloud API.

    Transient failures (connection errors, timeouts, HTTP 429/502/503/504) are
    retried with exponential backoff, except for configuration writes, which
    are never re-sent. An HTTP 401/403 triggers one transparent re-login.

    Pass ``open_auth=True`` to sign requests with the Siseli Open API headers
    (see :mod:`siseli.open_auth`). Pass ``http_client`` to reuse an existing
    :class:`httpx.AsyncClient`; it is then not closed by :meth:`close`.
    """

    def __init__(
        self,
        account: str,
        password: str,
        *,
        base_url: str = BASE_URL,
        timezone: str = "UTC",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff: float = DEFAULT_RETRY_BACKOFF,
        http_client: httpx.AsyncClient | None = None,
        open_auth: bool | tuple[str, str] = False,
    ) -> None:
        self._auth = Auth(account, password)
        self._timezone = timezone
        self._max_retries = max(0, max_retries)
        self._retry_backoff = max(0.0, retry_backoff)
        self._auth_lock = asyncio.Lock()
        self._owns_http = http_client is None
        self._http = http_client or httpx.AsyncClient(
            base_url=base_url,
            timeout=timeout,
            headers={"Accept": "application/json"},
        )
        if open_auth:
            from .open_auth import attach_open_auth

            if isinstance(open_auth, tuple):
                attach_open_auth(
                    self, app_id=open_auth[0], encrypted_secret=open_auth[1]
                )
            else:
                attach_open_auth(self)

    @property
    def http_client(self) -> httpx.AsyncClient:
        """The underlying HTTP client (for request hooks and diagnostics)."""
        return self._http

    @property
    def timezone(self) -> str:
        return self._timezone

    async def authenticate(self) -> None:
        async with self._auth_lock:
            await self._auth.login(self._http)

    async def close(self) -> None:
        if self._owns_http:
            await self._http.aclose()

    async def __aenter__(self) -> SiseliClient:
        try:
            await self.authenticate()
        except BaseException:
            await self.close()
            raise
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def _ensure_authenticated(self) -> None:
        if self._auth.is_authenticated():
            return
        async with self._auth_lock:
            # Another task may have logged in while we waited for the lock.
            if not self._auth.is_authenticated():
                await self._auth.login(self._http)

    async def _reauthenticate(self, stale_token: str) -> None:
        """Log in again unless another task already replaced *stale_token*."""
        async with self._auth_lock:
            info = self._auth.token_info
            if info is None or info.access_token == stale_token:
                self._auth.invalidate()
                await self._auth.login(self._http)

    async def _send(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """Send one authenticated request, retrying transient failures."""
        retryable = kwargs.pop("retry", True) and not path.startswith(
            _NON_RETRYABLE_PATHS
        )
        attempts = 1 + (self._max_retries if retryable else 0)
        reauthenticated = False
        attempt = 0
        while True:
            await self._ensure_authenticated()
            token = self._auth.access_token
            headers = {"IOT-Token": token, "IOT-Time-Zone": self._timezone}
            delay = self._retry_backoff * (2**attempt)
            try:
                response = await self._http.request(
                    method, path, headers=headers, **kwargs
                )
            except httpx.HTTPError as exc:
                attempt += 1
                if attempt < attempts:
                    _LOGGER.debug("Retrying %s %s after %s", method, path, exc)
                    await _sleep(delay)
                    continue
                raise NetworkError(
                    f"Request failed for {method} {path}: {exc}"
                ) from exc

            status = response.status_code
            if status in (401, 403):
                if not reauthenticated:
                    reauthenticated = True
                    await self._reauthenticate(token)
                    continue
                raise AuthenticationError(
                    f"HTTP {status} for {method} {path}", http_status=status
                )
            if status == 429 or status in _RETRYABLE_STATUSES:
                attempt += 1
                if attempt < attempts:
                    wait = _retry_after(response) if status == 429 else None
                    await _sleep(delay if wait is None else min(wait, 30.0))
                    continue
                if status == 429:
                    raise RateLimitError(
                        f"HTTP 429 for {method} {path}",
                        retry_after=_retry_after(response),
                    )
            if not response.is_success:
                raise NetworkError(
                    f"HTTP {status} for {method} {path}", http_status=status
                )
            return response

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
        """Send a request and return the ``data`` payload.

        Pass ``retry=False`` for anything with side effects.
        """
        response = await self._send(method, path, **kwargs)
        try:
            body = response.json()
        except ValueError as exc:
            raise InvalidResponseError(
                f"Response for {method} {path} is not valid JSON"
            ) from exc
        if not isinstance(body, dict):
            raise InvalidResponseError(
                f"Response for {method} {path} has unexpected shape"
            )
        if body.get("code") != 0:
            raise ApiError(body.get("code", -1), str(body.get("message", "")))
        return body.get("data")

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
        all_devices: list[Device] = []
        page = 1
        while True:
            devices, total = await fetch_device_list(
                self._request,
                page=page,
                count=DEFAULT_PAGE_SIZE,
            )
            all_devices.extend(devices)
            if not devices or len(all_devices) >= total:
                break
            page += 1
        return all_devices

    async def get_device(self, device_id: str) -> Device:
        return await fetch_device_details(self._request, device_id)

    async def get_device_state(
        self,
        device_id: str,
        *,
        data_source: int = DEFAULT_DATA_SOURCE,
    ) -> DeviceState:
        return await fetch_device_state(
            self._request, device_id, data_source=data_source
        )

    async def get_device_attributes(
        self,
        device_id: str,
        *,
        category: str = "",
        render_in: str = "",
    ) -> list[AttributeMetadata]:
        return await fetch_device_attributes(
            self._request,
            device_id,
            category=category,
            render_in=render_in,
        )

    async def get_device_attribute_groups(
        self,
        device_id: str,
        *,
        category: str = "",
        render_in: str = "",
    ) -> AttributeGroupSet:
        return await fetch_device_attribute_groups(
            self._request,
            device_id,
            category=category,
            render_in=render_in,
        )

    async def get_energy_flow(
        self,
        device_id: str,
        *,
        data_source: int = DEFAULT_DATA_SOURCE,
    ) -> EnergyFlow:
        return await fetch_energy_flow(
            self._request, device_id, data_source=data_source
        )

    async def get_attribute_history(
        self,
        device_id: str,
        keys: Iterable[str],
        *,
        from_time: datetime | str | None = None,
        to_time: datetime | str | None = None,
        page: int = 1,
        count: int = DEFAULT_PAGE_SIZE,
        order_by_time_asc: bool = True,
    ) -> HistorySeries:
        return await fetch_attribute_history(
            self._request,
            device_id,
            keys,
            from_time=from_time,
            to_time=to_time,
            page=page,
            count=count,
            order_by_time_asc=order_by_time_asc,
        )

    async def get_state_history(
        self,
        device_id: str,
        *,
        from_time: datetime | str | None = None,
        to_time: datetime | str | None = None,
        page: int = 1,
        count: int = DEFAULT_PAGE_SIZE,
        order_by_time_asc: bool = False,
    ) -> HistorySeries:
        return await fetch_state_history(
            self._request,
            device_id,
            from_time=from_time,
            to_time=to_time,
            page=page,
            count=count,
            order_by_time_asc=order_by_time_asc,
        )

    async def get_device_config(
        self,
        device_id: str,
        *,
        key: str = "",
        config_id: str = "",
    ) -> AttributeMetadata:
        return await fetch_device_config(
            self._request,
            device_id,
            key=key,
            config_id=config_id,
        )

    async def get_cached_device_configs(
        self,
        device_id: str,
    ) -> dict[str, AttributeMetadata]:
        return await fetch_cached_device_configs(self._request, device_id)

    async def read_device_configs(self, device_id: str) -> ConfigBatchRead:
        return await fetch_device_configs(self._request, device_id)

    async def get_device_config_batch(self, batch_read_id: str) -> ConfigBatchRead:
        return await fetch_device_config_batch_details(self._request, batch_read_id)

    async def set_device_config(
        self,
        device_id: str,
        *,
        key: str,
        value: Any,
        config_id: str = "",
    ) -> AttributeMetadata | None:
        return await write_device_config(
            self._request,
            device_id,
            key=key,
            value=value,
            config_id=config_id,
        )

    async def safe_set_device_config(
        self,
        device_id: str,
        *,
        key: str,
        value: Any,
        access: ConfigAccess = ConfigAccess.SAFE,
        battery_nominal_voltage: int | None = None,
        dry_run: bool = False,
    ) -> ConfigWriteResult:
        """Validated, serialized and verified write; never retried."""
        return await safe_write_device_config(
            self._request,
            device_id,
            key=key,
            value=value,
            access=access,
            battery_nominal_voltage=battery_nominal_voltage,
            dry_run=dry_run,
        )

    async def get_stations(
        self,
        *,
        page: int = 1,
        count: int = DEFAULT_PAGE_SIZE,
        name: str = "",
        connected_grid_type: str = "",
        state: str = "",
        station_type: str = "",
    ) -> list[Station]:
        result = await fetch_station_list(
            self._request,
            page=page,
            count=count,
            name=name,
            connected_grid_type=connected_grid_type,
            state=state,
            station_type=station_type,
        )
        return result.items

    async def get_all_stations(self) -> list[Station]:
        all_stations: list[Station] = []
        page = 1
        while True:
            result = await fetch_station_list(
                self._request,
                page=page,
                count=DEFAULT_PAGE_SIZE,
            )
            all_stations.extend(result.items)
            if not result.items or len(all_stations) >= result.total:
                break
            page += 1
        return all_stations

    async def get_station(self, station_id: str) -> Station:
        return await fetch_station_details(self._request, station_id)

    async def get_station_energy_flow(
        self,
        station_id: str,
        *,
        is_manual_refresh: bool = False,
    ) -> StationEnergyFlow:
        return await fetch_station_energy_flow(
            self._request,
            station_id,
            is_manual_refresh=is_manual_refresh,
        )

    async def get_station_income(
        self,
        station_id: str,
        aggregation: str,
        *,
        time: datetime | str | None = None,
    ) -> list[TimePoint]:
        return await fetch_station_income(
            self._request,
            station_id,
            aggregation,
            time=time,
        )

    async def get_station_summary(
        self,
        station_id: str,
        summary_category_key: str,
        aggregation: str,
        *,
        time: datetime | str | None = None,
    ) -> StationSummary:
        return await fetch_station_state_summary(
            self._request,
            station_id,
            summary_category_key,
            aggregation,
            time=time,
        )

    async def get_device_summary(
        self,
        device_id: str,
        aggregation: str,
        *,
        summary_category_key: str = ENERGY_SUMMARY_CATEGORY,
        time: datetime | str | None = None,
    ) -> StationSummary:
        return await fetch_device_state_summary(
            self._request,
            device_id,
            aggregation,
            summary_category_key=summary_category_key,
            time=time,
            tz=self._timezone,
        )

    async def get_device_energy_totals(self, device_id: str) -> dict[str, float | None]:
        """Return lifetime energy counters (kWh) keyed by property key."""
        summary = await self.get_device_summary(device_id, "total")
        return summary.to_totals()

    async def get_owner_summary(
        self,
        aggregation: str,
        *,
        summary_category_key: str = ENERGY_SUMMARY_CATEGORY,
        time: datetime | str | None = None,
    ) -> StationSummary:
        return await fetch_owner_state_summary(
            self._request,
            aggregation,
            summary_category_key=summary_category_key,
            time=time,
            tz=self._timezone,
        )

    async def get_device_generated_energy_daily(
        self,
        device_id: str,
        *,
        time: datetime | str | None = None,
    ) -> list[TimePoint]:
        return await fetch_device_generated_energy_daily(
            self._request, device_id, time=time, tz=self._timezone
        )

    async def get_device_power_daily_detail(
        self,
        device_id: str,
        *,
        time: datetime | str | None = None,
    ) -> dict[str, Any]:
        return await fetch_device_power_class_daily_detail(
            self._request, device_id, time=time, tz=self._timezone
        )

    async def get_latest_alarm(
        self,
        *,
        certificate_dtu_id: str = "",
        device_serial_number: str = "",
        page: int = 1,
        count: int = 1,
    ) -> Alarm | None:
        return await fetch_latest_alarm(
            self._request,
            certificate_dtu_id=certificate_dtu_id,
            device_serial_number=device_serial_number,
            page=page,
            count=count,
        )

    async def get_alarms(
        self,
        *,
        page: int = 1,
        count: int = DEFAULT_PAGE_SIZE,
        certificate_dtu_id: str = "",
        device_serial_number: str = "",
        from_time: datetime | str | None = None,
        to_time: datetime | str | None = None,
        is_processed: int | None = None,
        level: int | None = None,
        order_by_created_time_desc: bool = True,
    ) -> PagedResult[Alarm]:
        return await fetch_alarm_list(
            self._request,
            page=page,
            count=count,
            certificate_dtu_id=certificate_dtu_id,
            device_serial_number=device_serial_number,
            from_time=from_time,
            to_time=to_time,
            is_processed=is_processed,
            level=level,
            order_by_created_time_desc=order_by_created_time_desc,
        )

    async def get_alarm_report_headers(self) -> list[dict[str, Any]]:
        return await fetch_alarm_report_headers(self._request)

    async def get_alarm_report(self, record_id: str) -> dict[str, Any]:
        return await fetch_alarm_report_details(self._request, record_id)

    async def get_alarm_reports(
        self,
        *,
        page: int = 1,
        count: int = DEFAULT_PAGE_SIZE,
        dtu_id: str = "",
        state: int | None = None,
        created_from_time: datetime | str | None = None,
        created_to_time: datetime | str | None = None,
        order_by_created_at_asc: bool = False,
    ) -> PagedResult[AlarmReport]:
        return await fetch_alarm_reports(
            self._request,
            page=page,
            count=count,
            dtu_id=dtu_id,
            state=state,
            created_from_time=created_from_time,
            created_to_time=created_to_time,
            order_by_created_at_asc=order_by_created_at_asc,
        )

    async def get_dashboard_summary(self) -> DashboardSummary:
        return await fetch_dashboard_summary(self._request)

    async def get_dashboard_daily_generation_time_rank(
        self,
        *,
        asc: bool = False,
    ) -> list[StationRankEntry]:
        return await fetch_dashboard_daily_generation_time_rank(self._request, asc=asc)

    async def get_dashboard_station_distribution(
        self,
        *,
        east_longitude: float | None = None,
        west_longitude: float | None = None,
        north_latitude: float | None = None,
        south_latitude: float | None = None,
        level: int | None = None,
    ) -> list[LocationDistribution]:
        return await fetch_dashboard_station_distribution(
            self._request,
            east_longitude=east_longitude,
            west_longitude=west_longitude,
            north_latitude=north_latitude,
            south_latitude=south_latitude,
            level=level,
        )

    async def get_dashboard_monthly_generated_energy(self) -> list[TimePoint]:
        return await fetch_dashboard_monthly_generated_energy(self._request)

    async def get_dictionary(self, name: str) -> DictionaryData:
        return await fetch_dictionary(self._request, name)
