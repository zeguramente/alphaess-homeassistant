# Implementation Plan: AlphaESS Home Assistant Integration

**Branch**: `001-alphaess-ha-integration` | **Date**: 2026-10-18 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-alphaess-ha-integration/spec.md`

## Summary

A read-only Home Assistant custom integration (`alpha_ess`, distributed via HACS, built to core
standards) that connects to the AlphaESS cloud with AppID/AppSecret, creates one device per
system and exposes live power, daily energy, summary and static system values as sensors usable
in the Energy dashboard. All cloud access goes through `alphaess-aio`; two coordinators poll live
data every 60 s and energy data every 5 min. Setup, reauth and reconfigure run through a config
flow; diagnostics are redacted. Battery/EV control is a later feature.

## Technical Context

**Language/Version**: Python 3.14.2 (required by Home Assistant 2026.10)

**Primary Dependencies**: Home Assistant 2026.10 (min. `2026.10.0`), `alphaess-aio==1.0.1`
(1.0.0 + `py.typed`), `probatio` (provided by Home Assistant)

**Storage**: Home Assistant config entry only (AppID, AppSecret); no own storage

**Testing**: pytest with `pytest-homeassistant-custom-component==0.13.373`, `syrupy` snapshots,
`freezegun` via the `freezer` fixture, `pytest-cov`; the library client is mocked with
`autospec`, fed from recorded JSON fixtures (copied from `alphaess-aio/tests/fixtures`)

**Target Platform**: Home Assistant OS / Container / Core on Linux, installed via HACS

**Project Type**: Home Assistant custom integration (single project)

**Performance Goals**: ≤ 1.4 cloud requests per minute per system; setup completes in < 10 s with
a reachable cloud; no blocking I/O in the event loop

**Constraints**: Polling fixed at 60 s (live) / 5 min (energy); read-only; credentials never
logged; core-ready (core conventions, quality-scale tracking, core-like test layout)

**Scale/Scope**: 1 config entry per AlphaESS account, typically 1–2 systems; ~35 sensor
entities per system; 1 platform (`sensor`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Check | Pre-research | Post-design |
|---|---|---|---|
| I. Library-first | All cloud calls via `alphaess-aio` public API ([library contract](contracts/diagnostics-and-library.md)); missing `py.typed` fixed in library 1.0.1, not in the integration | ✅ | ✅ |
| II. HA conventions | Config flow only, coordinators, `runtime_data`, entity descriptions, `has_entity_name`, translations, reauth, reconfigure, diagnostics, stale-device removal; `quality_scale.yaml` with Bronze done, Silver targeted | ✅ | ✅ |
| III. Test-first, offline | Tests per platform/flow written before code; mocked client + fixtures; config flow 100 % coverage; snapshot tests for sensors and diagnostics | ✅ | ✅ |
| IV. Device & cloud | 60 s / 5 min fixed intervals; no write operations in v1; redaction of AppID, secret, serials; `None` → unknown | ✅ | ✅ |
| V. Simplicity | One platform, two coordinators, no options flow, no income/CO2 extras; typed with mypy strict | ✅ | ✅ |
| Workflow | ruff + mypy + pytest + hassfest gate; library change released before integration depends on it | ✅ | ✅ |

No violations; Complexity Tracking is empty.

## Project Structure

### Documentation (this feature)

```text
specs/001-alphaess-ha-integration/
├── plan.md              # This file
├── research.md          # Phase 0: decisions R1–R12
├── data-model.md        # Phase 1: config entry, runtime data, coordinator data
├── quickstart.md        # Phase 1: validation guide
├── contracts/
│   ├── config-flow.md               # setup/reauth/reconfigure steps, errors, aborts
│   ├── entities.md                  # sensor catalogue (keys, units, classes)
│   └── diagnostics-and-library.md   # diagnostics shape, used library API
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
custom_components/alpha_ess/
├── __init__.py          # async_setup_entry / async_unload_entry, stale-device removal
├── manifest.json        # domain alpha_ess, iot_class cloud_polling, integration_type hub
├── const.py             # DOMAIN, LOGGER, intervals, config keys
├── coordinator.py       # AlphaEssLiveCoordinator, AlphaEssEnergyCoordinator, runtime data type
├── config_flow.py       # user, reauth_confirm, reconfigure
├── entity.py            # AlphaEssEntity base (device info, unique id)
├── sensor.py            # entity descriptions + sensor classes, PARALLEL_UPDATES = 0
├── diagnostics.py       # redacted config entry diagnostics
├── icons.json
├── quality_scale.yaml
├── strings.json         # source of English texts
└── translations/
    ├── en.json          # generated from strings.json
    └── de.json

tests/
├── conftest.py          # mock client, mock config entry, init_integration
├── fixtures/            # recorded AlphaESS JSON responses
├── snapshots/           # syrupy snapshots
├── test_config_flow.py
├── test_init.py
├── test_sensor.py
└── test_diagnostics.py

hacs.json
pyproject.toml           # uv project: dev deps, ruff, mypy, pytest config
README.md                # install, setup, entities, sign conventions, known limitations
.github/workflows/       # lint + mypy + tests, hassfest, HACS validation
```

**Structure Decision**: Single-project HACS layout. The `custom_components/alpha_ess/` folder is
the unit that later moves to `homeassistant/components/alpha_ess/` in core; `tests/` mirrors
`tests/components/alpha_ess/` so a core port only changes import paths.

## Implementation Order (input for /speckit-tasks)

1. **Library prerequisite**: add `py.typed` to `alphaess-aio`, release 1.0.1.
2. **Scaffold**: `pyproject.toml`, manifest, `hacs.json`, const, CI, test fixtures.
3. **Story 1 (P1)**: config flow (`user`), coordinators, live sensors, system sensors, device —
   MVP.
4. **Story 2 (P2)**: energy coordinator and energy/summary sensors.
5. **Story 3 (P3)**: reauth, reconfigure, unavailability tests, stale devices, diagnostics.
6. **Polish**: German translations, README, `quality_scale.yaml`, manual quickstart run with
   real system (battery sign).

## Open Points

- Domain `alpha_ess` (research R2): confirmed by the maintainer on 2026-10-19.
- Battery power sign must be checked against a real system (research R6).

## Complexity Tracking

No constitution violations.
