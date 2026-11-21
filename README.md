# python-siseli

Python SDK for [Siseli Cloud](https://solar.siseli.com).

## Installation

```bash
pip install python-siseli
```

## Quick start

```python
import asyncio
from siseli import SiseliClient

async def main():
    async with SiseliClient("user@example.com", "secret", timezone="Europe/Warsaw") as client:
        # Discover devices
        devices = await client.get_devices()
        device = devices[0]
        print(f"Device: {device.name} ({device.id})")

        # Latest telemetry
        state = await client.get_device_state(device.id)
        grid = state.get("gridVoltage")
        if grid:
            print(f"Grid voltage: {grid.value_display} {grid.unit}")

        # Energy flow diagram
        flow = await client.get_energy_flow(device.id)
        if flow.battery:
            print(f"Battery: {flow.battery.value.value_display} {flow.battery.value.unit}")

asyncio.run(main())
```

## Client options

```python
SiseliClient(
    account, password,
    timezone="Europe/Warsaw",   # also used for "today"/"this month" in summaries
    timeout=30.0,
    max_retries=2,              # transient failures only, never for config writes
    retry_backoff=0.5,          # seconds, doubled on each retry
    http_client=None,           # reuse your own httpx.AsyncClient (not closed by the SDK)
    open_auth=False,            # sign requests with the Siseli Open API headers
)
```

* An expired token is refreshed transparently; an HTTP 401/403 triggers one
  re-login and retry.
* Connection errors, timeouts and HTTP 429/502/503/504 are retried with
  exponential backoff.
* `open_auth=True` adds the `IOT-Open-*` signature headers. The application
  secret used for this is taken from the official web client; it is only
  obfuscated, not confidential, and may be rotated by the vendor. Pass
  `open_auth=(app_id, encrypted_secret)` to override it.

## Errors

All errors derive from `SiseliError`:

| Exception | Meaning | Typical handling (e.g. Home Assistant) |
|---|---|---|
| `AuthenticationError` | Login rejected, or HTTP 401/403 after a re-login | start re-auth flow |
| `RateLimitError` (a `NetworkError`) | HTTP 429, see `.retry_after` | back off |
| `NetworkError` | Timeouts, connection errors, other HTTP errors (`.http_status`) | mark unavailable, retry later |
| `ApiError` | API returned a non-zero `code` | report `.code` / `.message` |
| `InvalidResponseError` | Body is not JSON or has an unexpected shape | log, retry later |

## Writing configuration

Use `safe_set_device_config()`; the low-level `set_device_config()` performs no
validation. Writes are allow-listed, range-checked, serialized per device,
never retried and verified by reading the value back (the result is
`UNKNOWN`, not success, when that is inconclusive). Battery-voltage keys need an
explicit `battery_nominal_voltage`, which is cross-checked against the live
`batteryVoltage` reading. See [`docs/api.md`](docs/api.md) for details.

```python
from siseli import ConfigAccess

result = await client.safe_set_device_config(
    device.id, key="buzzerEnabled", value=False, dry_run=True
)
```

## Development

```bash
pip install -e ".[dev]"
ruff check siseli tests && mypy siseli && pytest
```

## Development plan

See [`roadmap.md`](roadmap.md) for the full development plan.

## API documentation

See [`docs/api.md`](docs/api.md).