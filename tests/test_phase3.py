from __future__ import annotations

from datetime import UTC, datetime

import pytest

from siseli.alarms import fetch_alarm_list, fetch_latest_alarm
from siseli.config import fetch_cached_device_configs, fetch_device_configs
from siseli.dashboard import fetch_dashboard_summary
from siseli.dictionary import fetch_dictionary
from siseli.history import fetch_attribute_history, fetch_state_history
from siseli.state import fetch_device_attribute_groups, fetch_device_attributes
from siseli.station import fetch_station_energy_flow, fetch_station_list, fetch_station_state_summary


@pytest.mark.asyncio
async def test_fetch_device_metadata_parses_attributes_and_groups() -> None:
    async def request(method: str, path: str, **kwargs):
        if path.endswith('/gatherAttributes/v1'):
            return [
                {
                    'key': 'gridVoltage',
                    'valueType': 1,
                    'name': 'Grid Voltage',
                    'nameDisplay': 'Grid Voltage',
                    'unit': 'V',
                    'isStateAttribute': True,
                }
            ]
        return {
            'gatherProtocolVersionId': 'proto-1',
            'attributesGroups': [
                {
                    'id': 'group-1',
                    'key': 'inverter_setting',
                    'category': 3,
                    'name': 'Inverter setting',
                    'description': 'Settings',
                    'attributes': [
                        {
                            'key': 'powerSavingEnable',
                            'name': 'Power Saving Enable',
                            'nameDisplay': 'Power Saving Enable',
                            'valueType': 2,
                            'isConfigAttribute': True,
                            'isWritableConfigAttribute': True,
                            'enumValues': [
                                {'value': '0', 'text': 'Disabled'},
                                {'value': '1', 'text': 'Enabled'},
                            ],
                        }
                    ],
                }
            ],
        }

    attributes = await fetch_device_attributes(request, 'device-1')
    groups = await fetch_device_attribute_groups(request, 'device-1')

    assert attributes[0].key == 'gridVoltage'
    assert attributes[0].is_state_attribute is True
    assert groups.gather_protocol_version_id == 'proto-1'
    assert groups.groups[0].attributes[0].enum_values[1].name == 'Enabled'


@pytest.mark.asyncio
async def test_fetch_history_parses_records() -> None:
    async def request(method: str, path: str, **kwargs):
        if path.endswith('/keys/history/v1'):
            return {
                'page': 1,
                'count': 2,
                'total': 2,
                'payload': {
                    'timeSeries': ['2026-07-23T13:19:27Z', '2026-07-23T13:14:04Z'],
                    'fields': {'gridVoltage': [237.4, None]},
                    'formatters': {'gridVoltage': {'unit': 'V'}},
                },
            }
        return {
            'page': 1,
            'count': 2,
            'total': 2,
            'payload': {
                'timeSeries': ['2026-07-23T13:19:27Z', '2026-07-23T13:14:04Z'],
                'fields': {'gridVoltage': [{'vd': '237.4'}, {'vd': '238.6'}]},
            },
        }

    selected = await fetch_attribute_history(request, 'device-1', ['gridVoltage'])
    records = await fetch_state_history(request, 'device-1')

    assert selected.fields['gridVoltage'] == [237.4, None]
    assert selected.records[1].values['gridVoltage'] is None
    assert records.records[0].values['gridVoltage'] == '237.4'
    assert records.time_series[0] == datetime(2026, 7, 23, 13, 19, 27, tzinfo=UTC)


@pytest.mark.asyncio
async def test_fetch_config_cache_parses_metadata() -> None:
    async def request(method: str, path: str, **kwargs):
        if path.endswith('/configs/cache/get'):
            return {
                'powerSavingEnable': {
                    'key': 'powerSavingEnable',
                    'name': 'Power Saving Enable',
                    'nameDisplay': 'Power Saving Enable',
                    'valueType': 2,
                    'value': '1',
                    'isWritableConfigAttribute': True,
                }
            }
        return {
            'id': 'batch-1',
            'deviceId': 'device-1',
            'scene': 1,
            'requestKeys': ['powerSavingEnable'],
            'targetConfig': {
                'powerSavingEnable': {
                    'key': 'powerSavingEnable',
                    'name': 'Power Saving Enable',
                    'nameDisplay': 'Power Saving Enable',
                    'valueType': 2,
                    'value': '1',
                }
            },
            'isFinished': True,
            'createdAt': '2026-07-23T13:19:27Z',
        }

    cached = await fetch_cached_device_configs(request, 'device-1')
    batch = await fetch_device_configs(request, 'device-1')

    assert cached['powerSavingEnable'].key == 'powerSavingEnable'
    assert cached['powerSavingEnable'].is_writable_config_attribute is True
    assert batch.id == 'batch-1'
    assert 'powerSavingEnable' in batch.target_config


@pytest.mark.asyncio
async def test_fetch_station_data_parses_flow_and_summary() -> None:
    async def request(method: str, path: str, **kwargs):
        if path == '/apis/station/list':
            return {
                'page': 1,
                'count': 1,
                'total': 1,
                'list': [
                    {
                        'id': 'station-1',
                        'name': 'Home',
                        'timezone': 'Europe/Warsaw',
                        'longitude': 20.0,
                        'latitude': 50.0,
                    }
                ],
            }
        if path == '/apis/station/energy/flow':
            return {
                'isSupportFlow': True,
                'time': '2026-07-23T13:19:27Z',
                'pvPanelFlow': {
                    'key': 'pv',
                    'localeTitle': 'PV',
                    'value': {
                        'key': 'pvPower',
                        'value': 123.4,
                        'valueDisplay': '123.4',
                        'nameDisplay': 'PV Power',
                        'unit': 'W',
                    },
                    'extraValues': [
                        {
                            'key': 'pvVoltage',
                            'value': 45.6,
                            'valueDisplay': '45.6',
                            'nameDisplay': 'PV Voltage',
                            'unit': 'V',
                        }
                    ],
                },
            }
        return {
            'category': {'id': 'cat-1', 'key': 'generation', 'name': 'Generation'},
            'properties': [
                {
                    'property': {'key': 'pvPower'},
                    'timePoints': [
                        {
                            'time': '2026-07-23T00:00:00Z',
                            'timeDisplay': '00:00',
                            'value': 1.23,
                            'isRealValue': True,
                        }
                    ],
                    'hasRealTimePoints': True,
                }
            ],
            'hasRealTimePoints': True,
        }

    stations = await fetch_station_list(request, count=1)
    flow = await fetch_station_energy_flow(request, 'station-1')
    summary = await fetch_station_state_summary(request, 'station-1', 'generation', 'daily')

    assert stations.items[0].name == 'Home'
    assert flow.is_support_flow is True
    assert flow.pv_panel is not None
    assert flow.pv_panel.extra_values[0].key == 'pvVoltage'
    assert summary.category is not None
    assert summary.properties[0].time_points[0].value == 1.23


@pytest.mark.asyncio
async def test_fetch_alarm_dashboard_and_dictionary_helpers() -> None:
    async def request(method: str, path: str, **kwargs):
        if path == '/apis/alarm/getLatestAlarm':
            return {'id': 'alarm-1', 'deviceName': 'Inverter', 'level': 2}
        if path == '/apis/alarm/query/list':
            return {
                'page': 1,
                'count': 1,
                'total': 1,
                'list': [{'id': 'alarm-1', 'deviceName': 'Inverter', 'level': 2}],
            }
        if path == '/apis/dashboard/summary/commons':
            return {
                'dailyProducedQuantity': 12.3,
                'stationStateSummary': [{'state': 1, 'count': 2, 'stateDict': 'Online'}],
            }
        return {
            'levels': [
                {'value': 1, 'name': 'Notice'},
                {'value': 2, 'name': 'Warning'},
            ]
        }

    latest = await fetch_latest_alarm(request)
    alarms = await fetch_alarm_list(request)
    summary = await fetch_dashboard_summary(request)
    dictionary = await fetch_dictionary(request, 'alarm')

    assert latest is not None and latest.level == 2
    assert alarms.items[0].device_name == 'Inverter'
    assert summary.station_state_summary[0].label == 'Online'
    assert dictionary.values['levels'][1].name == 'Warning'
