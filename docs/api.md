# Solar SISeli API Documentation

Каталог собран обратной разработкой по HAR-записям веб-интерфейса Siseli Cloud. Последняя сверка выполнена 12 октября 2026 года по предоставленному HAR-файлу `BIG_solar.siseli.com.har`.

> Важно: это reverse-engineered документация. Она описывает реальные вызовы из HAR, но не гарантирует полноту всех полей, бизнес-правил и кодов ошибок сервера.

## Источник и объем

- Базовый URL: `https://solar.siseli.com`
- В последнем проверенном HAR наблюдалось `225` запросов к `/apis/*` и `86` уникальных сочетаний метода и пути (query string не учитывается).
- Таблицы ниже — накопленный каталог, объединяющий этот и более ранние HAR/сведения из permissions ответа. Поэтому не каждый endpoint из каталога обязательно присутствует в последнем capture.
- Большинство вызовов требуют заголовок `IOT-Token`; в последнем HAR он присутствует у запросов после входа в систему.

## Аутентификация

1. Браузерный клиент выполняет `POST /apis/login/account` с JSON-телом `account` и `password`. В наблюдаемом клиентском потоке пароль передавался как MD5-хеш; SDK также вычисляет MD5 от переданного открытого пароля перед отправкой.
2. В ответ сервер возвращает `accessToken` и `refreshToken` внутри `data`.
3. Для дальнейших вызовов клиент передает токен в заголовке `IOT-Token`.
4. Дополнительно клиент отправляет заголовок `IOT-Time-Zone` со значением часового пояса браузера.

`refreshToken` и срок его действия присутствуют в ответе login. Отдельный endpoint обновления access token в рассмотренных HAR не обнаружен. Текущий SDK не использует refresh token: когда access token истекает, он повторно выполняет login.

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
- Успешный результат обычно имеет `code = 0`. HTTP 200 не гарантирует успех операции: API может вернуть ненулевой `code` и сообщение об ошибке в JSON-теле.
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
| `POST` | `/apis/device/batch/upgrade/list` | Поиск пакетных операций обновления устройств. | `—` | `count, deviceName, deviceSerialNumber, firmwareName, fromTime, page, protocolName, status, toTime` | `null` | Последний HAR: HTTP 200, `code=20210`, `message="no rights"` |
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
| `POST` | `/apis/deviceOverView/pvInverterPowerClass/daily/detail` | Детальный временной ряд показателей PV-инвертора за день. | `deviceId` | `time` | `dict` | В последнем HAR `data` содержит `page`, `count`, `total`, `payload`; в `payload` наблюдались `timeSeries`, `fields`, `formatters`, `fieldInfo` |
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
| `GET` | `/apis/dictionary/data/deviceBatchUpgrade` | Получение справочника для пакетного обновления устройств. | `—` | `—` | `null` | Последний HAR: HTTP 200, `code=20210`, `message="no rights"` |
| `GET` | `/apis/dictionary/data/alarm` | Получение справочника `alarm`. | `—` | `—` | `dict` | — |
| `GET` | `/apis/dictionary/data/device` | Получение справочника `device`. | `—` | `—` | `dict` | — |
| `GET` | `/apis/dictionary/data/dtu` | Получение справочника `dtu`. | `—` | `—` | `dict` | Обнаружен в permissions ответа `/apis/login/account` |
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
| `POST` | `/apis/remote/device/config/write` | Удаленная запись параметра конфигурации устройства. | `deviceId` | `id, key, value` | `dict` | Обнаружен в permissions ответа `/apis/login/account` |
| `POST` | `/apis/remote/device/config/write/records` | История операций удаленной записи конфигурации. | `—` | `count, deviceId, fromTime, key, orderByCreatedAtAsc, page, state, toTime` | `dict` | Обнаружен в permissions ответа `/apis/login/account` |
| `POST` | `/apis/remote/device/configs/cache/clear` | Очистка кэша удаленных конфигураций устройства. | `deviceId` | `—` | `NoneType` | Обнаружен в permissions ответа `/apis/login/account` |
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

## SDK: поддерживаемые возможности

SDK реализует только часть endpoint-каталога. Публичные методы `SiseliClient` на момент последней сверки:

| Возможность | Методы SDK | Endpoint |
| --- | --- | --- |
| Аутентификация и повторный вход после истечения access token | `authenticate()` | `POST /apis/login/account` |
| Список устройств и подробности устройства | `get_devices()`, `get_all_devices()`, `get_device()` | `/apis/device/list`, `/apis/device/details` |
| Состояние, атрибуты, группы и поток энергии устройства | `get_device_state()`, `get_device_attributes()`, `get_device_attribute_groups()`, `get_energy_flow()` | `/apis/deviceState/simple/*`, `/apis/device/query/attribute/group` |
| История атрибутов и записей состояния | `get_attribute_history()`, `get_state_history()` | `/apis/deviceState/simple/attribute/*/v1` |
| Удаленная конфигурация | `get_device_config()`, `get_cached_device_configs()`, `read_device_configs()`, `get_device_config_batch()`, `set_device_config()`, `safe_set_device_config()` | `/apis/remote/device/config*` |
| Станции, потоки, доход и сводки | `get_stations()`, `get_all_stations()`, `get_station()`, `get_station_energy_flow()`, `get_station_income()`, `get_station_summary()` | `/apis/station/*`, `/apis/stationOverView/*` |
| Сводки устройства и владельца, дневная выработка и детали мощности | `get_device_summary()`, `get_device_energy_totals()`, `get_owner_summary()`, `get_device_generated_energy_daily()`, `get_device_power_daily_detail()` | `/apis/deviceOverView/*`, `/apis/ownerOverView/*` |
| Тревоги и отчеты о тревогах | `get_latest_alarm()`, `get_alarms()`, `get_alarm_report_headers()`, `get_alarm_report()`, `get_alarm_reports()` | `/apis/alarm/*` |
| Сводка и аналитика dashboard | `get_dashboard_summary()`, `get_dashboard_daily_generation_time_rank()`, `get_dashboard_station_distribution()`, `get_dashboard_monthly_generated_energy()` | `/apis/dashboard/summary/*` |
| Справочники | `get_dictionary()` | `/apis/dictionary/data/{name}` |

Остальные пути в каталоге обнаружены в HAR или permissions, но не имеют соответствующего публичного метода SDK.

### Безопасная удаленная запись конфигурации

Для обычной записи используйте `safe_set_device_config()`: метод проверяет ключ, уровень доступа и значение, сериализует записи для одного устройства, а после единственной попытки записи читает значение повторно. Публичный `set_device_config()` отправляет ключ и значение напрямую; он не применяет allowlist, проверку диапазонов, проверку уровня доступа или read-back, поэтому не является безопасной заменой.

```python
from siseli import ConfigAccess, ConfigWriteStatus

result = await client.safe_set_device_config(
    device.id,
    key="buzzerEnabled",
    value=True,
)

if result.status is ConfigWriteStatus.APPLIED:
    print("Значение установлено:", result.current)
elif result.status is ConfigWriteStatus.UNKNOWN:
    print("Результат записи не подтвержден; не повторяйте запись автоматически")
```

- По умолчанию разрешен только риск `SAFE`. Для параметров с риском `ADVANCED` или `CRITICAL` передайте соответствующий `access=ConfigAccess.ADVANCED` или `access=ConfigAccess.CRITICAL`. Неизвестные и не включенные в `CONFIG_SPECS` ключи отклоняются; перечень и диапазоны намеренно ограничены.
- Для ключей напряжения батареи обязательно явно передайте `battery_nominal_voltage` (`12`, `24` или `48`). Необходимые соседние значения конфигурации SDK читает сам; если такое чтение не удается или проверка порядка напряжений не проходит, запись не отправляется.
- `dry_run=True` выполняет чтения и проверки, но не отправляет запись и возвращает результат со статусом `DRY_RUN`. Если значение уже установлено, запись также пропускается; результат имеет статус `APPLIED` и сообщение `already set`.
- SDK сериализует вызовы безопасной записи для одного устройства и выдерживает не менее трех секунд между фактическими попытками записи.
- SDK не повторяет попытку записи. После успешного ответа или неопределенного исхода он сверяет значение чтением: подтвержденное значение дает `APPLIED`, а тайм-аут/сетевая неопределенность или несовпадение read-back — `UNKNOWN`. В результате также доступны `requested`, `previous`, `current`, `error_code` и `message`. `UNKNOWN` не означает, что устройство точно не применило изменение: не повторяйте такую запись автоматически.
- Неподдерживаемый ключ/значение вызывает `ConfigValidationError`, недостаточный доступ — `ConfigAccessDenied`. Другие ошибки API и HTTP 4xx, кроме HTTP 408 и 429, считаются определенным отказом и вызывают `ConfigRejected`; коды API 71301 и 70138 и прочие неопределенные сетевые ошибки проходят проверку read-back и могут дать `UNKNOWN`.
- `settingDeviceOutputSourcePriority` не входит в список разрешенных для записи ключей: отображаемое облаком значение `0` (`SUB` / SBU) противоречит порядку PI30, а полное соответствие значений не подтверждено. Чтение этого ключа отдельно не запрещено.

### Форматы overview

- `stateAttributeSummary/category/{daily|monthly|yearly|total}` возвращает объект категории и список `properties`. У каждого свойства есть метаданные `property` (ключ, название, единица) и `timePoints` с полями `time`, `timeDisplay`, `value`, `isRealValue`.
- Для `pvInverterElectricityQuantityClass` в HAR обнаружены, среди прочих, `pvGeneratedEnergy`, `buyElectricityQuantity`, `sellElectricityQuantity`, `chargeElectricityQuantity`, `dischargeElectricityQuantity`, `consumeElectricityQuantity`; единица — `kWh`.
- `generatedEnergy/daily` возвращает список точек выработки за день (`time`, `timeDisplay`, `value`/`generatedEnergy`, `isRealValue`).
- В вызовах последнего HAR `time` для дневной, месячной и годовой агрегации имел формат `YYYY-MM-DD`, `YYYY-MM` и `YYYY` соответственно. Для `total` передавалась временная метка ISO 8601.
- Эти формы и поля наблюдались в конкретном capture; они не являются гарантией контракта сервера для всех типов устройств и учетных записей.

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
