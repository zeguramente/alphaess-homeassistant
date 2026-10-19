# Research: AlphaESS Home Assistant Integration

**Feature**: [spec.md](spec.md) | **Date**: 2026-10-18

Sources checked: local Home Assistant core checkout (`../core`, 2026.10.0.dev, commit of
2026-09-27), PyPI (`homeassistant` 2026.10.2, `pytest-homeassistant-custom-component` 0.13.373,
`alphaess-aio` 1.0.0), the `alphaess-aio` repository, and the existing HACS integration
`CharlesGillanders/homeassistant-alphaESS`.

## R1 — Target Home Assistant and Python version

- **Decision**: Target Home Assistant 2026.10 (minimum `2026.10.0` in `hacs.json`), Python 3.14.2.
- **Rationale**: Current stable release; core requires Python ≥ 3.14.2, which is installed locally
  via uv. The custom-component test harness (`pytest-homeassistant-custom-component==0.13.373`)
  pins `homeassistant==2026.10.2` and requires Python ≥ 3.14.
- **Alternatives considered**: Supporting older HA releases — rejected; core-readiness (FR-018)
  requires current APIs (`probatio` schemas, typed `ConfigEntry` runtime data), and older releases
  would need compatibility code (Principle V, YAGNI).

## R2 — Integration domain

- **Decision**: Domain `alpha_ess`, display name "Alpha ESS".
- **Rationale**: The popular HACS integration `homeassistant-alphaESS` already uses the domain
  `alphaess` and has its brand assets registered under `custom_integrations/alphaess`. Two custom
  integrations with the same domain cannot be installed side by side and would overwrite each
  other's folder. `alpha_ess` follows Home Assistant's snake_case brand naming and is free in core.
- **Alternatives considered**: `alphaess` (old manifest) — conflicts as described;
  `alphaess_cloud` — longer and not the brand name.
- **Follow-up**: The user may prefer another domain; changing it later breaks existing installs,
  so confirm before the first release.

## R3 — Library version and gaps

- **Decision**: Depend on `alphaess-aio==1.0.1`, a patch release that adds a `py.typed` marker.
  Until it is released, development uses the local checkout (`../alphaess-aio`) as path source.
- **Rationale**: PyPI 1.0.0 is the squash-merge of the hand-maintained client (same public API as
  the local `refactor/hand-maintained-client` branch) and covers everything v1 needs:
  `get_ess_list`, `get_last_power_data`, `get_one_date_energy_by_sn`, `get_sum_data_for_customer`,
  the exception hierarchy, a shared-session parameter and a timeout. It ships no `py.typed`, so
  mypy treats it as untyped, which breaks the strict-typing requirement (Constitution V, HA
  Platinum rule `strict-typing`). Per Principle I the fix goes into the library.
- **Compatibility**: Library requires `aiohttp>=3.9.3`, `pydantic>=2.10.3`; HA 2026.10 pins
  `aiohttp==3.14.3`, `pydantic==2.13.4` — compatible.
- **Alternatives considered**: Inline type stubs in the integration — violates Principle I.

## R4 — Data fetching and polling

- **Decision**: Two coordinators per config entry, both iterating over all systems of the
  account:
  1. **Live coordinator**, every 60 s: `get_last_power_data(sys_sn)` per system.
  2. **Energy coordinator**, every 5 min: `get_one_date_energy_by_sn(sys_sn, today)` and
     `get_sum_data_for_customer(sys_sn)` per system.
  The system list (`get_ess_list`) is fetched once during setup and stored in runtime data.
- **Rationale**: Matches FR-013 and Constitution IV. Per system and hour: 60 live + 24 energy
  requests ≈ 1.4 requests/min, well below the request frequencies AlphaESS allows for these
  endpoints. One failing endpoint only makes its own entities unavailable.
- **Alternatives considered**: One coordinator at 60 s for everything — 3× the requests for data
  that changes slowly; one coordinator per system — more objects without benefit for typical
  1–2 systems.

## R5 — Daily energy and long-term statistics

- **Decision**: Daily energy sensors use `state_class: total_increasing`. The query date is
  "today" in Home Assistant's configured time zone. Summary values that are daily (`eload`) also
  use `total_increasing`; lifetime PV (`epvtotal`) uses `total_increasing`.
- **Rationale**: The values are daily counters that reset at midnight; `total_increasing` treats
  the drop as a meter reset, which the Energy dashboard handles. Because the energy endpoint is
  queried by date, it cannot return yesterday's total after the date changes (edge case "counted
  twice").
- **Alternatives considered**: `state_class: total` with `last_reset` from `theDate` — more
  code, same result while the system and Home Assistant share a time zone.
- **Assumption**: The AlphaESS system and Home Assistant are in the same time zone.

## R6 — Sign conventions and units

- **Decision**:
  - Grid power keeps AlphaESS's sign (positive = import, negative = export); additional derived
    sensors "grid import power" = max(pgrid, 0) and "grid export power" = max(−pgrid, 0).
  - Battery power keeps AlphaESS's sign; the direction (positive = discharging is expected) MUST
    be verified against the real system during implementation and documented in the README.
  - Self-consumption/self-sufficiency are delivered as fractions 0–1 and shown as 0–100 %.
  - Nominal PV power (kWp) is shown in kW with device class `power`, since Home Assistant has no
    kWp unit.
- **Rationale**: FR-007, FR-010, FR-012; the fixture shows `pgrid: 3230` while importing.

## R7 — Config flow, unique ID, reauth and reconfigure

- **Decision**:
  - Unique ID of the config entry = AppID.
  - `user` step: AppID + AppSecret (password selector); validation calls `get_ess_list`; aborts
    with `no_systems` if the account has no systems (edge case resolved: abort with explanation).
  - `reauth_confirm` step: AppSecret only; AppID stays fixed.
  - `reconfigure` step: AppSecret only; changing the AppID means a different account and requires
    adding a new entry.
  - Schemas use `probatio` (843 of 844 core config flows use it as of 2026.10).
- **Rationale**: FR-001–FR-004; matches the current core reference pattern (`fumis`).
- **Alternatives considered**: Allowing AppID changes in reconfigure with a system-overlap
  check — more logic for a rare case.

## R8 — Devices and stale devices

- **Decision**: One device per system: identifiers `(alpha_ess, sys_sn)`, manufacturer
  "Alpha ESS", model = inverter model, serial number = `sys_sn`, name = "Alpha ESS {sys_sn}".
  Battery model is a diagnostic sensor. On setup, devices whose serial number is no longer in the
  system list are removed from the device registry.
- **Rationale**: FR-005, Story 3 scenario 5 (stale devices). A device has only one model field.

## R9 — Optional detail sensors

- **Decision**: Per-string PV, per-phase grid and per-phase inverter output sensors are created
  only if the value is not `None` in the first live refresh, and are disabled by default.
  EV power is created only if `pev` is not `None`.
- **Rationale**: FR-008; edge case "missing value never shown as 0".

## R10 — Packaging, CI and core-readiness

- **Decision**: Repository layout of a HACS custom integration
  (`custom_components/alpha_ess/`, `hacs.json`), with `strings.json` as the source of English
  texts and `translations/en.json` generated from it; German in `translations/de.json`.
  `quality_scale.yaml` tracks rules (Bronze required, Silver target). Tests use
  `pytest-homeassistant-custom-component`, `syrupy` snapshots and `snapshot_platform`, mirroring
  the core test layout so porting only changes import paths (`tests.common` ↔
  `pytest_homeassistant_custom_component.common`). CI runs ruff, mypy, pytest, `hassfest` and the
  HACS validation action.
- **Rationale**: FR-018 (HACS first, core-ready), Constitution II/III.
- **Alternatives considered**: Developing inside the core checkout — slower iteration and
  requires core review before any user can install it.

## R11 — Entity platforms in v1

- **Decision**: Only the `sensor` platform.
- **Rationale**: v1 is read-only (Clarification 2026-10-18); all data are measurements or
  diagnostic values. No `binary_sensor` is needed (no boolean data in the read endpoints).

## R12 — Optional summary figures

- **Decision**: Income, tree and CO2 equivalents are not exposed in v1.
- **Rationale**: The spec marks them optional; income needs a currency unit taken from the API at
  runtime, which adds code for little value (Principle V). They can be added later without
  breaking existing entities.
