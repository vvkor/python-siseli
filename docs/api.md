# Solar SISeli API Documentation

Документация составлена по HAR-файлу `/home/runner/work/python-siseli/python-siseli/solar.siseli.com.har` и отражает фактически наблюдавшиеся запросы веб-интерфейса.

> Важно: это reverse-engineered документация. Она описывает реальные вызовы из HAR, но не гарантирует полноту всех полей, бизнес-правил и кодов ошибок сервера.

## Источник и объем

- Базовый URL: `https://solar.siseli.com`
- Наблюдалось API-запросов: `405`
- Уникальных endpoint'ов: `108`
- Большинство вызовов требуют заголовок `IOT-Token`; в HAR он присутствует у `372` запросов после логина.

## Аутентификация

1. Клиент выполняет `POST /apis/login/account` с JSON-телом `account` и `password`.
2. В ответ сервер возвращает `accessToken` и `refreshToken` внутри `data`.
3. Для дальнейших вызовов клиент передает токен в заголовке `IOT-Token`.
4. Дополнительно клиент отправляет заголовок `IOT-Time-Zone` со значением часового пояса браузера.

### Пример запроса логина

```http
POST /apis/login/account HTTP/1.1
Content-Type: application/json; charset=utf-8
Accept: application/json

{
  "account": "<login>",
  "password": "<password-or-client-hash>"
}
```

### Пример успешного ответа

```json
{
  "code": 0,
  "message": "Success",
  "localMessage": "Success",
  "data": {
    "accessToken": "***",
    "accessTokenWillExpiredAt": "<timestamp>",
    "refreshToken": "***",
    "refreshTokenWillExpiredAt": "<timestamp>",
    "authId": "<auth-id>",
    "account": "<login>"
  }
}
```

## Общие соглашения

- Формат запроса: в основном `application/json`; GET-параметры передаются в query string.
- Формат ответа для JSON API: `{ code, message, localMessage, data }`.
- Успешный результат обычно имеет `code = 0`.
- Для бинарных загрузок (`/apis/resource/download/*`) тело ответа не JSON, а файл/медиа-контент.
- Часто используются поля пагинации: `page`, `count`.
- Для сортировки встречаются флаги вида `orderBy...Asc`, `orderBy...Desc`, а также `timeAsc`.
- Для периодов используются поля `fromTime`, `toTime`, `createdFromTime`, `createdToTime`, `time`.

### Типовой JSON-ответ

```json
{
  "code": 0,
  "message": "Success",
  "localMessage": "Success",
  "data": {}
}
```

## Домены API

- [alarm](#alarm)
- [currency](#currency)
- [dashboard](#dashboard)
- [device](#device)
- [deviceOffset](#deviceoffset)
- [deviceOverView](#deviceoverview)
- [deviceSort](#devicesort)
- [deviceState](#devicestate)
- [dictionary](#dictionary)
- [dtu](#dtu)
- [geo](#geo)
- [getInfo](#getinfo)
- [getRouters](#getrouters)
- [login](#login)
- [owner](#owner)
- [ownerOverView](#owneroverview)
- [portal](#portal)
- [remote](#remote)
- [resource](#resource)
- [rest](#rest)
- [sim](#sim)
- [simcard](#simcard)
- [station](#station)
- [stationOverView](#stationoverview)
- [user](#user)

## alarm

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/alarm/report/alarmList/headers` | Получение набора колонок для отчета по тревогам. | `—` | `—` | `list` | — |
| `GET` | `/apis/alarm/report/record/details` | Получение подробной информации по записи тревоги/отчета. | `id` | `—` | `dict` | — |
| `POST` | `/apis/alarm/getLatestAlarm` | Операции с тревогами и их отчетами. | `—` | `certificateDtuID, count, deviceSerialNumber, page` | `dict` | — |
| `POST` | `/apis/alarm/query/list` | Поиск списка тревог по фильтрам. | `—` | `certificateDtuID, count, deviceSerialNumber, fromTime, isProcessed, level, orderByCreatedTimeDesc, page, toTime` | `dict` | — |
| `POST` | `/apis/alarm/report/alarmList/export` | Экспорт отчета по тревогам. | `—` | `dtuID, fieldNames, fromTime, remark, toTime` | `dict` | — |
| `POST` | `/apis/alarm/report/record/list` | Поиск списка тревог по фильтрам. | `—` | `count, createdFromTime, createdToTime, dtuID, orderByCreatedAtAsc, page, state` | `dict` | — |

## currency

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/currency/list` | Справочник доступных валют. | `—` | `—` | `list` | — |

## dashboard

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/apis/dashboard/summary/commons` | Данные для виджетов и сводных панелей dashboard. | `—` | `—` | `dict` | POST без JSON-полей в теле в наблюдаемом вызове |
| `POST` | `/apis/dashboard/summary/station/dailyGenerationTimeRank` | Данные для виджетов и сводных панелей dashboard. | `asc` | `—` | `list` | POST без JSON-полей в теле в наблюдаемом вызове |
| `POST` | `/apis/dashboard/summary/station/distribution/location` | Данные для виджетов и сводных панелей dashboard. | `—` | `eastLongitude, level, northLatitude, southLatitude, westLongitude` | `list` | — |
| `POST` | `/apis/dashboard/summary/station/generatedEnergy/monthly` | Данные для виджетов и сводных панелей dashboard. | `—` | `—` | `list` | POST без JSON-полей в теле в наблюдаемом вызове |

## device

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/device/details` | Получение карточки устройства или деталей связанного отчета. | `deviceId` | `—` | `dict` | — |
| `GET` | `/apis/device/linkage/rule/detail` | Получение правила или схемы связей устройства. | `attributeCategory, deviceId` | `—` | `dict` | — |
| `GET` | `/apis/device/query/attribute/group` | Получение групп атрибутов устройства. | `category, deviceId, renderIn` | `—` | `dict` | — |
| `GET` | `/apis/device/report/export/records/details` | Получение карточки устройства или деталей связанного отчета. | `id` | `—` | `dict` | — |
| `GET` | `/apis/device/report/get/daily/excel/header` | Получение конфигурации колонок экспортного отчета по устройствам. | `deviceId` | `—` | `list` | — |
| `GET` | `/apis/device/report/get/list/excel/header` | Получение конфигурации колонок экспортного отчета по устройствам. | `—` | `—` | `list` | Колонки экспортного отчета |
| `GET` | `/apis/device/report/get/monthly/excel/header` | Получение конфигурации колонок экспортного отчета по устройствам. | `deviceId` | `—` | `list` | — |
| `GET` | `/apis/device/report/get/yearly/excel/header` | Получение конфигурации колонок экспортного отчета по устройствам. | `deviceId` | `—` | `list` | — |
| `GET` | `/apis/device/state/count` | Счетчики состояний устройств. | `—` | `—` | `list` | — |
| `GET` | `/apis/device/upgrade/device/names` | Справочник значений для фильтров обновления устройств. | `—` | `—` | `list` | — |
| `GET` | `/apis/device/upgrade/firmware/names` | Справочник значений для фильтров обновления устройств. | `—` | `—` | `list` | — |
| `GET` | `/apis/device/upgrade/protocol/names` | Справочник значений для фильтров обновления устройств. | `—` | `—` | `list` | — |
| `POST` | `/apis/device/external/list` | Поиск списка устройств по фильтрам. | `—` | `mainDeviceId` | `list` | — |
| `POST` | `/apis/device/gather/protocol/open/search` | Поиск открытых протоколов/профилей опроса устройств. | `—` | `applyModeCategory, count, page` | `dict` | — |
| `POST` | `/apis/device/list` | Поиск списка устройств по фильтрам. | `—` | `applyModeCategory, count, deviceSortKey, dtuDtuid, dtuId, exportType, fieldNames, gatherProtocolNumber, name, orderByCreatedAtAsc, orderByInstalledAtAsc, orderByNameAsc, orderByProducingPowerAsc, orderBySerialNumberAsc, orderByStateAsc, page, remark, serialNumber, softwareVersion, state, stationId` | `dict` | — |
| `POST` | `/apis/device/report/daily` | Формирование отчета по устройству за период. | `—` | `fieldNames, fromTime, id, remark, toTime` | `dict` | — |
| `POST` | `/apis/device/report/export/records/list` | Поиск или получение деталей экспортированных отчетов по устройствам. | `—` | `count, deviceName, deviceSerialNumber, fromTime, page, state, timeAsc, toTime, type` | `dict` | — |
| `POST` | `/apis/device/report/monthly` | Формирование отчета по устройству за период. | `—` | `fieldNames, fromTime, id, remark, toTime` | `dict` | — |
| `POST` | `/apis/device/report/yearly` | Формирование отчета по устройству за период. | `—` | `fieldNames, fromTime, id, remark, toTime` | `dict` | — |
| `POST` | `/apis/device/upgrade/list` | Поиск списка устройств по фильтрам. | `—` | `count, deviceName, deviceSerialNumber, firmwareName, fromTime, page, protocolName, status, toTime` | `dict` | — |

## deviceOffset

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/apis/deviceOffset/totally` | Суммарные смещения/итоги по устройству. | `—` | `deviceId` | `list` | — |

## deviceOverView

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/apis/deviceOverView/generatedEnergy/daily` | Агрегированные показатели устройства по времени и категориям. | `deviceId` | `time` | `list` | — |
| `POST` | `/apis/deviceOverView/stateAttributeSummary/category/daily` | Агрегированные показатели устройства по времени и категориям. | `deviceId, summaryCategoryKey` | `time` | `dict` | — |
| `POST` | `/apis/deviceOverView/stateAttributeSummary/category/monthly` | Агрегированные показатели устройства по времени и категориям. | `deviceId, summaryCategoryKey` | `time` | `dict` | — |
| `POST` | `/apis/deviceOverView/stateAttributeSummary/category/total` | Агрегированные показатели устройства по времени и категориям. | `deviceId, summaryCategoryKey` | `time` | `dict` | — |
| `POST` | `/apis/deviceOverView/stateAttributeSummary/category/yearly` | Агрегированные показатели устройства по времени и категориям. | `deviceId, summaryCategoryKey` | `time` | `dict` | — |

## deviceSort

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/deviceSort/sorts/all` | Справочник типов/сортов устройств. | `—` | `—` | `list` | — |

## deviceState

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/deviceState/simple/energy/flow/v1` | Текущее энергетическое состояние/потоки устройства. | `dataSource, deviceId` | `—` | `dict` | — |
| `GET` | `/apis/deviceState/simple/gatherAttributes/v1` | Список атрибутов устройства для отображения. | `category, deviceId, renderIn` | `—` | `list` | — |
| `GET` | `/apis/deviceState/simple/state/latest/v1` | Последнее состояние устройства. | `dataSource, deviceId` | `—` | `dict` | — |
| `POST` | `/apis/deviceState/simple/attribute/keys/history/v1` | История значений выбранных ключей/атрибутов устройства. | `—` | `count, deviceId, fromTime, keys, orderByTimeAsc, page, toTime` | `dict` | — |
| `POST` | `/apis/deviceState/simple/attribute/record/list/v1` | Список записей телеметрии/состояний устройства. | `—` | `count, deviceId, fromTime, orderByTimeAsc, page, toTime` | `dict` | — |

## dictionary

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/dictionary/data/alarm` | Получение справочника `alarm`. | `—` | `—` | `dict` | — |
| `GET` | `/apis/dictionary/data/device` | Получение справочника `device`. | `—` | `—` | `dict` | — |
| `GET` | `/apis/dictionary/data/report` | Получение справочника `report`. | `—` | `—` | `dict` | — |
| `GET` | `/apis/dictionary/data/simcard` | Получение справочника `simcard`. | `—` | `—` | `dict` | — |
| `GET` | `/apis/dictionary/data/station` | Получение справочника `station`. | `—` | `—` | `dict` | — |

## dtu

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/dtu/count/general` | Сводный счетчик DTU. | `—` | `—` | `dict` | — |
| `GET` | `/apis/dtu/models` | Справочник моделей DTU. | `—` | `—` | `list` | — |
| `POST` | `/apis/dtu/query/list` | Поиск списка DTU по фильтрам. | `—` | `count, dtuid, isActived, isOnline, isUpgradeAuto, model, page` | `dict` | — |
| `POST` | `/apis/dtu/replace/list` | История или список замен DTU. | `—` | `count, deviceId, deviceSerialNumber, dtuID, orderByReplacedAtAsc, page` | `dict` | — |
| `POST` | `/apis/dtu/select/dtu` | Получение одной записи DTU по идентификатору. | `dtuId` | `—` | `dict` | POST без JSON-полей в теле в наблюдаемом вызове |

## geo

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/geo/location/ip/lookup/lite` | Геолокация по IP-адресу. | `ip` | `—` | `dict` | — |
| `GET` | `/apis/geo/location/ip/lookup/myip/lite` | Геолокация текущего IP. | `—` | `—` | `dict` | — |

## getInfo

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/getInfo` | Получение информации о текущем пользователе и его правах. | `—` | `—` | `dict` | — |

## getRouters

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/getRouters` | Получение дерева маршрутов/меню интерфейса. | `—` | `—` | `list` | — |

## login

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/apis/login/account` | Аутентификация пользователя по учетной записи. | `—` | `account, password` | `dict` | — |

## owner

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/owner/report/export/records/details` | Отчеты владельца/пользователя за период. | `id` | `—` | `dict` | — |
| `GET` | `/apis/owner/report/get/monthly/excel/header` | Отчеты владельца/пользователя за период. | `—` | `—` | `list` | Колонки экспортного отчета |
| `GET` | `/apis/owner/report/get/yearly/excel/header` | Отчеты владельца/пользователя за период. | `—` | `—` | `list` | Колонки экспортного отчета |
| `POST` | `/apis/owner/report/export/records/list` | Отчеты владельца/пользователя за период. | `—` | `count, fromTime, page, state, timeAsc, toTime, type` | `dict` | — |
| `POST` | `/apis/owner/report/monthly` | Отчеты владельца/пользователя за период. | `—` | `fieldNames, fromTime, id, remark, toTime` | `dict` | — |
| `POST` | `/apis/owner/report/yearly` | Отчеты владельца/пользователя за период. | `—` | `fieldNames, fromTime, id, remark, toTime` | `dict` | — |

## ownerOverView

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/apis/ownerOverView/select/ownerStatistics` | Сводные показатели владельца по станциям. | `—` | `—` | `dict` | POST без JSON-полей в теле в наблюдаемом вызове |
| `POST` | `/apis/ownerOverView/station/stateAttributeSummary/category/daily` | Сводные показатели владельца по станциям. | `summaryCategoryKey` | `time` | `dict` | — |
| `POST` | `/apis/ownerOverView/station/stateAttributeSummary/category/monthly` | Сводные показатели владельца по станциям. | `summaryCategoryKey` | `time` | `dict` | — |
| `POST` | `/apis/ownerOverView/station/stateAttributeSummary/category/total` | Сводные показатели владельца по станциям. | `summaryCategoryKey` | `time` | `dict` | — |
| `POST` | `/apis/ownerOverView/station/stateAttributeSummary/category/yearly` | Сводные показатели владельца по станциям. | `summaryCategoryKey` | `time` | `dict` | — |

## portal

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/portal/info` | Получение общих сведений о портале. | `—` | `—` | `dict` | — |

## remote

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/remote/device/configs/read/details` | Детали пакетного чтения удаленной конфигурации. | `batchReadId` | `—` | `dict` | — |
| `GET` | `/apis/remote/device/state/report/fast/supported` | Проверка поддержки быстрого удаленного отчета состояния. | `deviceId` | `—` | `bool` | — |
| `POST` | `/apis/remote/device/config/read` | Удаленное чтение параметра или конфигурации устройства. | `deviceId` | `id, key` | `dict` | В HAR встречался код ошибки 71301 |
| `POST` | `/apis/remote/device/configs/cache/get` | Получение кэша удаленных конфигураций устройства. | `deviceId` | `—` | `dict` | POST без JSON-полей в теле в наблюдаемом вызове |
| `POST` | `/apis/remote/device/configs/read` | Операции удаленного управления устройствами и DTU. | `deviceId` | `—` | `dict` | POST без JSON-полей в теле в наблюдаемом вызове |
| `POST` | `/apis/remote/dtu/restart` | Удаленный перезапуск DTU. | `dtuId` | `—` | `NoneType` | POST без JSON-полей в теле в наблюдаемом вызове |

## resource

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/resource/download/media` | Скачивание защищенного медиа-ресурса по `resid`. | `resid, save` | `—` | `empty, raw` | Защищенная загрузка файла |
| `GET` | `/apis/resource/download/public/media` | Скачивание публичного медиа-ресурса по `resid`. | `resid` | `—` | `raw` | Публичная загрузка файла |

## rest

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/apis/rest/api/list` | Список API-операций или журнала API с фильтром логирования. | `—` | `count, isLoggable, page` | `dict` | — |

## sim

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/sim/card/report/details` | Отчетность по SIM-картам. | `id` | `—` | `dict` | — |
| `GET` | `/apis/sim/card/report/headers` | Отчетность по SIM-картам. | `—` | `—` | `list` | — |
| `POST` | `/apis/sim/card/report/export` | Отчетность по SIM-картам. | `—` | `fieldNames, iccids, remark` | `dict` | — |
| `POST` | `/apis/sim/card/report/list` | Отчетность по SIM-картам. | `—` | `count, createdFromTime, createdToTime, page, state` | `dict` | — |

## simcard

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/apis/simcard/search` | Поиск SIM-карт по фильтрам. | `—` | `count, dataBalanceWarningCode, expiryWarningCode, isActived, page, status, supplierCode` | `dict` | — |

## station

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/station/details` | Получение карточки станции. | `stationId` | `—` | `dict` | — |
| `GET` | `/apis/station/energy/flow` | Энергетические потоки станции. | `isManualRefresh, stationId` | `—` | `dict` | — |
| `GET` | `/apis/station/report/export/records/details` | Получение карточки станции. | `id` | `—` | `dict` | — |
| `GET` | `/apis/station/report/get/monthly/excel/header` | Получение колонок экспортного отчета по станциям. | `—` | `—` | `list` | Колонки экспортного отчета |
| `GET` | `/apis/station/report/get/station/list/excel/header` | Получение колонок экспортного отчета по станциям. | `—` | `—` | `list` | Колонки экспортного отчета |
| `GET` | `/apis/station/report/get/yearly/excel/header` | Получение колонок экспортного отчета по станциям. | `—` | `—` | `list` | Колонки экспортного отчета |
| `GET` | `/apis/station/state/count` | Счетчики состояний станций. | `—` | `—` | `list` | — |
| `POST` | `/apis/station/list` | Поиск списка станций по фильтрам. | `—` | `connectedGridType, count, name, orderByConnectedGridTypeAsc, orderByCreatedAtAsc, orderByInstalledAtAsc, orderByInstalledCapacityAsc, orderByNameAsc, orderByStateAsc, orderByStationTypeAsc, page, state, stationType` | `dict` | — |
| `POST` | `/apis/station/report/export/records/list` | Поиск или получение деталей экспортированных отчетов по станциям. | `—` | `count, fromTime, page, state, stationName, timeAsc, toTime, type` | `dict` | — |
| `POST` | `/apis/station/report/monthly` | Формирование отчета по станции за период. | `—` | `fieldNames, fromTime, id, remark, toTime` | `dict` | — |

## stationOverView

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `POST` | `/apis/stationOverView/income/daily` | Агрегированные показатели станции по времени и категориям. | `stationId` | `time` | `list` | — |
| `POST` | `/apis/stationOverView/income/monthly` | Агрегированные показатели станции по времени и категориям. | `stationId` | `time` | `list` | — |
| `POST` | `/apis/stationOverView/income/total` | Агрегированные показатели станции по времени и категориям. | `stationId` | `time` | `list` | — |
| `POST` | `/apis/stationOverView/income/yearly` | Агрегированные показатели станции по времени и категориям. | `stationId` | `time` | `list` | — |
| `POST` | `/apis/stationOverView/stateAttributeSummary/category/daily` | Агрегированные показатели станции по времени и категориям. | `stationId, summaryCategoryKey` | `time` | `dict` | — |
| `POST` | `/apis/stationOverView/stateAttributeSummary/category/monthly` | Агрегированные показатели станции по времени и категориям. | `stationId, summaryCategoryKey` | `time` | `dict` | — |
| `POST` | `/apis/stationOverView/stateAttributeSummary/category/yearly` | Агрегированные показатели станции по времени и категориям. | `stationId, summaryCategoryKey` | `time` | `dict` | — |

## user

| Method | Path | Назначение | Query params | Body fields | Response `data` | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `GET` | `/apis/user/currency` | Текущая валюта пользователя. | `—` | `—` | `dict` | — |
| `POST` | `/apis/user/currency/setting` | Изменение валюты пользователя. | `currencyCode` | `—` | `dict` | POST без JSON-полей в теле в наблюдаемом вызове |
| `POST` | `/apis/user/log/personal/search` | Поиск персонального журнала действий. | `—` | `count, fromTime, orderByTimeDesc, page, toTime` | `dict` | — |
| `POST` | `/apis/user/personal/superiors/direct` | Поиск непосредственных руководителей/связанных пользователей. | `—` | `name, uid` | `list` | — |
| `POST` | `/apis/user/select/iotUserInfo` | Получение профиля пользователя. | `—` | `—` | `dict` | POST без JSON-полей в теле в наблюдаемом вызове |
| `POST` | `/apis/user/select/userThemeColors` | Получение пользовательских цветов темы. | `—` | `—` | `dict` | POST без JSON-полей в теле в наблюдаемом вызове |
| `POST` | `/apis/user/update/iotUserInfo` | Обновление профиля пользователя. | `—` | `iconResid, name, remark` | `NoneType` | — |

## Наблюдаемые параметры по типам задач

### Пагинация

- `page` — номер страницы
- `count` — размер страницы / лимит записей

### Периоды и агрегации

- `fromTime`, `toTime` — границы периода
- `createdFromTime`, `createdToTime` — границы периода создания записи
- `time` — момент или период агрегации для overview-методов
- Пути `daily`, `monthly`, `yearly`, `total` задают тип агрегации в самом endpoint.

### Идентификаторы

- `deviceId` — идентификатор устройства
- `stationId` — идентификатор станции
- `dtuId` / `dtuID` / `dtuid` — идентификатор DTU (в HAR встречаются разные варианты имени)
- `id` — универсальный идентификатор записи отчета/деталей
- `resid` — идентификатор медиа-ресурса

### Фильтры состояния и сортировки

- `state`, `status`, `isProcessed`, `isActived`, `isOnline`, `isUpgradeAuto`
- `orderBy...Asc`, `orderBy...Desc`, `timeAsc`, `asc`
- `level`, `type`, `category`, `summaryCategoryKey`, `renderIn`

## Известные ограничения документации

- В документации приведены только поля, реально встреченные в HAR.
- Не все ответы содержали удобные для автоматического восстановления структуры `data`; для части методов указан только тип (`dict`, `list`, `bool`, `NoneType`, `raw`).
- Реальные обязательные поля, диапазоны значений и бизнес-валидации нужно проверять дополнительным тестированием или исходниками бэкенда.
