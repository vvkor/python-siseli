# Roadmap

This document describes the long-term vision and development plan for the **python-siseli** ecosystem.

The project consists of two independent but closely related repositories:

- **python-siseli** — a standalone Python SDK for Siseli Cloud.
- **ha-siseli** — a Home Assistant integration built on top of the SDK.

---

# Vision

The primary goal is to build a complete, well-documented and reusable implementation of the Siseli Cloud API.

The SDK should become the reference open-source implementation of the API and be useful outside Home Assistant.

The Home Assistant integration should contain as little API-specific logic as possible and rely entirely on the SDK.

---

# Project Architecture

```
                    Siseli Cloud
                         │
                         ▼
                 python-siseli SDK
                         │
        ┌────────────────┴────────────────┐
        ▼                                 ▼
 Home Assistant                    Any Python project
   ha-siseli                    CLI / Scripts / Jupyter
```

---

# Design Principles

## SDK First

All communication with Siseli Cloud belongs inside **python-siseli**.

The SDK is responsible for:

- authentication;
- HTTP client;
- request serialization;
- response parsing;
- retries;
- exceptions;
- business logic;
- typed models.

The SDK must have **no dependency on Home Assistant**.

---

## Thin Home Assistant Integration

The Home Assistant integration should only contain Home Assistant specific functionality:

- Config Flow
- Options Flow
- DataUpdateCoordinator
- Entity creation
- Diagnostics
- Services

Everything else should be delegated to the SDK.

---

# Development Phases

## Phase 1 — Reverse Engineering

Goal:

Understand and document the Siseli Cloud API.

Tasks:

- [x] analyze HAR captures (`solar.siseli.com.har` — 405 requests);
- [x] identify endpoints (108 unique endpoints discovered);
- [x] document requests;
- [x] document responses;
- [x] identify authentication flow (`POST /apis/login/account` → `IOT-Token`);
- [x] identify required headers (`IOT-Token`, `IOT-Time-Zone`);
- [x] classify API domains (25 domains: alarm, dashboard, device, deviceState, station, etc.);
- [ ] discover undocumented endpoints.

Deliverables:

- [x] API documentation (`docs/api.md`)
- [x] endpoint catalog (108 endpoints across 20 domains)
- [x] reverse engineering notes (embedded in `docs/api.md`)

Status:

**Done**

---

## Phase 2 — Core SDK

Implement the minimum feature set required to communicate with Siseli Cloud.

Features:

- [x] authentication
- [x] token handling
- [x] device discovery
- [x] device details
- [x] latest telemetry
- [x] energy flow

Goal:

A developer should be able to authenticate and retrieve the current state of a device with only a few lines of Python.

Deliverables:

- [x] `siseli/` package (`pyproject.toml`, `siseli/__init__.py`)
- [x] `siseli/const.py` — base URL, defaults
- [x] `siseli/exceptions.py` — exception hierarchy
- [x] `siseli/models/` — typed dataclasses (`TokenInfo`, `Device`, `DeviceState`, `EnergyFlow`, `FlowNode`, `StateAttribute`)
- [x] `siseli/auth.py` — `Auth` class (MD5 login, token expiry check)
- [x] `siseli/device.py` — `fetch_device_list`, `fetch_device_details`
- [x] `siseli/state.py` — `fetch_device_state`, `fetch_energy_flow`
- [x] `siseli/client.py` — `SiseliClient` public entry point (context manager, auto-reauth)

Status:

**Done**

---

## Phase 3 — Full SDK

Expand the SDK to support the remaining public functionality.

Status:

**Not Started**

### Device State

- current state
- grouped attributes
- attribute metadata

### History

- historical keys
- historical values
- pagination

### Configuration

- read configuration
- cached configuration
- batch reads
- configuration writes

### Stations

- station details
- station energy flow
- station summaries

### Alarms

- latest alarms
- alarm history
- alarm reports

### Dashboard

- aggregated statistics
- summaries

### Dictionaries

- lookup tables
- enums
- metadata

---

## Phase 4 — Advanced Features

Investigate advanced capabilities that are not yet fully understood.

Goal:

Unlock functionality beyond the standard public API surface.

Status:

**Not Started**

### Fast Reporting

Research the following endpoints:

```
GET  /remote/device/state/report/fast/supported
POST /remote/device/state/report/fast/start
POST /remote/device/state/report/fast/stop
```

Potential goal:

Increase telemetry refresh rate while the client is actively monitoring a device.

---

### Passthrough API

Research:

```
POST /remote/device/passthrough
```

This endpoint may provide direct access to the inverter protocol and could unlock functionality not exposed by the public API.

---

### Configuration Model

Build a complete model of all configuration parameters.

For every parameter identify:

- key
- type
- unit
- valid range
- default value
- writable/read-only status
- description

---

# SDK Architecture

Planned structure:

```
siseli/

    client.py
    auth.py

    device.py
    station.py

    state.py
    history.py

    config.py
    alarms.py

    models/

    exceptions.py
    const.py
```

Future additions may include:

```
passthrough.py
firmware.py
dashboard.py
dictionary.py
```

---

# Home Assistant Architecture

```
Config Flow
      │
      ▼
SiseliClient
      │
      ▼
DataUpdateCoordinator
      │
      ▼
Entities
```

Entities must never communicate with the API directly.

All data should be provided by the Coordinator.

---

# Home Assistant MVP

The first public release should expose the most useful telemetry.

Examples include:

- Battery SOC
- Battery Voltage
- Battery Current
- Battery Power

- PV Voltage
- PV Current
- PV Power

- Grid Voltage
- Grid Frequency
- Grid Power

- Output Voltage
- Output Frequency
- Load Power

- Inverter State

Configuration changes are intentionally excluded from the MVP.

---

# Future Home Assistant Features

After the initial release:

- historical statistics
- energy dashboard support
- alarm sensors
- binary sensors
- diagnostics
- device actions
- firmware information

Eventually:

- configuration editor
- remote commands
- Fast Reporting control

---

# Long-Term Goals

## Typed Models

Replace generic dictionaries with strongly typed models.

Possible implementations:

- dataclasses
- Pydantic models

---

## Automatic Metadata

Use API metadata to automatically build:

- attribute registry
- enums
- units
- display names
- configuration definitions

The goal is to minimize hardcoded knowledge inside the SDK.

---

## Comprehensive Documentation

Maintain high-quality documentation alongside the implementation.

Documentation should include:

- API reference
- endpoint catalog
- reverse engineering notes
- architecture
- examples
- changelog

---

# Guiding Principle

The SDK is the foundation of the ecosystem.

Every feature should first be implemented in **python-siseli** and only then exposed through **ha-siseli**.

This keeps the SDK reusable, the Home Assistant integration lightweight, and both projects easier to maintain.
