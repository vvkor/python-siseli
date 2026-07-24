"""SiseliClient — the main public entry point for the SDK."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Iterable

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
    write_device_config,
)
from .const import BASE_URL, DEFAULT_DATA_SOURCE, DEFAULT_PAGE_SIZE, DEFAULT_TIMEOUT
from .dashboard import (
    fetch_dashboard_daily_generation_time_rank,
    fetch_dashboard_monthly_generated_energy,
    fetch_dashboard_station_distribution,
    fetch_dashboard_summary,
)
from .device import fetch_device_details, fetch_device_list
from .dictionary import fetch_dictionary
from .exceptions import ApiError, NetworkError
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


class SiseliClient:
    """Async client for the Siseli Cloud API."""

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

    async def authenticate(self) -> None:
        await self._auth.login(self._http)

    async def close(self) -> None:
        await self._http.aclose()

    async def __aenter__(self) -> SiseliClient:
        await self.authenticate()
        return self

    async def __aexit__(self, *_: Any) -> None:
        await self.close()

    async def _ensure_authenticated(self) -> None:
        if not self._auth.is_authenticated():
            await self._auth.login(self._http)

    async def _request(self, method: str, path: str, **kwargs: Any) -> Any:
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
            if len(all_devices) >= total:
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
    ) -> AttributeMetadata:
        return await write_device_config(
            self._request,
            device_id,
            key=key,
            value=value,
            config_id=config_id,
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
            if len(all_stations) >= result.total:
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
