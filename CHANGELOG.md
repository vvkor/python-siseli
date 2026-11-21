# Changelog

## 0.3.0

### Changed (breaking)
- All datetimes parsed from API payloads (`Device.last_data_at`, `HistoryRecord.time`, `Alarm.created_at`, …) are now timezone-aware; timestamps without an offset are treated as UTC. Code comparing them with naive `datetime.now()` must use `datetime.now(UTC)`.
- Login HTTP 429 raises `RateLimitError` and HTTP 408/5xx raise `NetworkError` instead of `AuthenticationError`, so integrations do not start a re-auth flow when merely throttled.
- `TokenInfo.access_token_expires_at` / `refresh_token_expires_at` are typed `datetime | None`.

### Fixed
- Open API signing only applies to requests for the client's own host, so a shared `http_client` is not affected for other hosts.
- `get_all_devices()` / `get_all_stations()` no longer loop forever when a page comes back empty.
- HTTP 401/403 now re-login once and retry, then raise `AuthenticationError` (previously `NetworkError`); HTTP 429 raises `RateLimitError`.
- Concurrent requests share a single login; tokens count as expired 30 s early; naive timestamps are treated as UTC.
- `safe_set_device_config()` returns `UNKNOWN` (after read-back) instead of raising when the write response cannot be parsed.
- Parsers tolerate JSON `null` for lists/objects; non-JSON bodies raise `InvalidResponseError`.
- "Now" for device/owner summaries uses the client timezone instead of the machine's local zone.
- `aggregation` and dictionary names are validated before being put into URL paths.
- The client is closed when login fails inside `async with`.
- Power values with an unknown unit are `None` instead of being multiplied by 1000.
- Account names are masked in logs.

### Added
- Retry with exponential backoff for transient failures. Requests with side effects pass `retry=False` to `_request` (config writes do) and are never re-sent.
- `SiseliClient(http_client=..., open_auth=..., max_retries=..., retry_backoff=...)`.
- `RateLimitError`, `InvalidResponseError`.
- Battery nominal voltage is cross-checked against the live reading before voltage writes (`verify_battery_voltage=False` disables).
- `rated_apparent_power` sensor field (`load_apparent_power` kept as a deprecated alias).
- `py.typed`, `LICENSE`, CI workflow (ruff, mypy, pytest on 3.11-3.13); tests run before publishing.

### Removed
- Tracked `__pycache__` files.
