---

description: "Task list for the AlphaESS Home Assistant integration (v1, read-only)"
---

# Tasks: AlphaESS Home Assistant Integration

**Input**: Design documents from `specs/001-alphaess-ha-integration/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Required. Constitution Principle III (test-first, offline) and SC-006/SC-007 demand
automated tests for the config flow, data refresh, error handling and every entity type. Write
each test task first and confirm it fails before the matching implementation task.

**Organization**: Tasks are grouped by user story (spec.md: US1 = P1 live power, US2 = P2
energy, US3 = P3 resilience). Stories 4 and 5 (control) are out of scope.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 — only in user story phases

## Path Conventions

- Repository root: `/home/msz/python/homeasssistant/alphaess-homeassistant` (all paths below are
  relative to it unless they start with `../alphaess-aio/`)
- Integration: `custom_components/alpha_ess/`; tests: `tests/`
- Library repository: `../alphaess-aio/`
- Reference integration for current Home Assistant patterns: `../core/homeassistant/components/fumis/`
  and its tests in `../core/tests/components/fumis/`

## Conventions for all code tasks

- Follow the personal Python style (names over comments, Google-style docstrings, `_` prefix for
  module-internal helpers, `typing.override` on overridden methods) and Constitution V.
- Form schemas use `probatio` (not `voluptuous`), as in `../core/homeassistant/components/fumis/config_flow.py`.
- Test helpers come from `pytest_homeassistant_custom_component.common` (core equivalent:
  `tests.common`), e.g. `MockConfigEntry`, `snapshot_platform`, `async_fire_time_changed`.
- Library imports only from the public API: `alphaessaio` (`AlphaEssAPI`, `AlphaEssAuth`,
  `AlphaEssAuthError`, `AlphaEssConnectionError`, `AlphaEssRequestError`, `AlphaEssError`) and
  `alphaessaio.models` (`EssSystem`, `LastPowerData`, `DailyEnergy`, `SystemSummary`).
- Catch `AlphaEssAuthError` before `AlphaEssRequestError` (it is a subclass).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Library prerequisite and project initialization

- [X] T001 In `../alphaess-aio/`, run `git fetch --tags` and create branch `fix/py-typed` from tag `v1.0.0` (commit `511d045`; the local `main` is still at 0.2.0). Add an empty `../alphaess-aio/alphaessaio/py.typed`, add `[tool.setuptools.package-data]` with `alphaessaio = ["py.typed"]` to `../alphaess-aio/pyproject.toml`, set `__version__ = "1.0.1"` in `../alphaess-aio/alphaessaio/__init__.py`, add a "v1.0.1 — add py.typed marker" entry to `../alphaess-aio/CHANGELOG.md`, run `uv build` and verify with `unzip -l dist/alphaess_aio-1.0.1-py3-none-any.whl | grep py.typed`. Publishing to PyPI is done by the maintainer and is not part of this task.
- [X] T002 Run `git init` in the repository root and create `.gitignore` covering `.venv/`, `__pycache__/`, `.pytest_cache/`, `.mypy_cache/`, `.ruff_cache/`, `.coverage`, `htmlcov/`, `dist/`; create the empty directories `custom_components/alpha_ess/translations/`, `tests/fixtures/`, `.github/workflows/`.
- [X] T003 Create `pyproject.toml`: `[project]` name `alpha-ess-homeassistant`, version `0.1.0`, `requires-python = ">=3.14.2"`, no runtime dependencies; `[dependency-groups] dev = ["pytest-homeassistant-custom-component==0.13.373", "alphaess-aio==1.0.1", "mypy==2.3.1", "ruff==0.16.8", "pytest-cov==7.1.0"]`; `[tool.uv.sources] alphaess-aio = { path = "../alphaess-aio", editable = true }` (temporary until 1.0.1 is on PyPI); `[tool.pytest.ini_options]` with `testpaths = ["tests"]`, `asyncio_mode = "auto"`, `asyncio_default_fixture_loop_scope = "function"`; `[tool.mypy]` with `python_version = "3.14"`, `strict = true`, `packages = ["custom_components.alpha_ess"]`; `[tool.ruff]` `target-version = "py314"` and copy the `[tool.ruff.lint]` `select`/`ignore` lists from `../core/pyproject.toml`. Add `.python-version` containing `3.14.2`. Run `uv sync` and confirm it succeeds.
- [X] T004 [P] Create `hacs.json` with `{"name": "Alpha ESS", "homeassistant": "2026.10.0", "render_readme": true}`.
- [X] T005 [P] Create `.github/workflows/ci.yml` (on push/pull_request: `astral-sh/setup-uv`, `uv sync`, `uv run ruff check .`, `uv run ruff format --check .`, `uv run mypy`, `uv run pytest --cov=custom_components.alpha_ess --cov-fail-under=95`) and `.github/workflows/validate.yml` (jobs `home-assistant/actions/hassfest@master` and `hacs/action@main` with `category: integration`).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Manifest, constants, shared coordinator/entity base and test harness used by all stories

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [X] T006 Create `custom_components/alpha_ess/manifest.json` with keys in this order: `"domain": "alpha_ess"`, `"name": "Alpha ESS"`, `"codeowners": ["@zeguramente"]`, `"config_flow": true`, `"documentation": "https://github.com/zeguramente/alphaess-homeassistant"`, `"integration_type": "hub"`, `"iot_class": "cloud_polling"`, `"issue_tracker": "https://github.com/zeguramente/alphaess-homeassistant/issues"`, `"loggers": ["alphaessaio"]`, `"requirements": ["alphaess-aio==1.0.1"]`, `"version": "0.1.0"` (adjust both URLs if the GitHub repository gets another name).
- [X] T007 [P] Create `custom_components/alpha_ess/const.py` with `DOMAIN: Final = "alpha_ess"`, `LOGGER = logging.getLogger(__package__)`, `MANUFACTURER: Final = "Alpha ESS"`, `CONF_APP_ID: Final = "app_id"`, `CONF_APP_SECRET: Final = "app_secret"`, `LIVE_UPDATE_INTERVAL: Final = timedelta(seconds=60)`, `ENERGY_UPDATE_INTERVAL: Final = timedelta(minutes=5)`.
- [X] T008 [P] Copy `getEssList.json`, `getLastPowerData.json`, `getOneDateEnergyBySn.json`, `getSumDataForCustomer.json` from `../alphaess-aio/tests/fixtures/` to `tests/fixtures/`. Add `tests/fixtures/getEssList_two_systems.json` (same envelope, second system with `"sysSn": "AL0000000000001"`, `"minv": "SMILE-G3-S5"`, `"mbat": "SMILE-G3-BAT-10.1P"`) and `tests/fixtures/getLastPowerData_minimal.json` (only `ppv`, `pload`, `pgrid`, `pbat`, `soc` set; `pev`, `ppvDetail`, `pgridDetail`, `prealL1..3` all `null`).
- [X] T009 Create `custom_components/alpha_ess/coordinator.py` foundation: `@dataclass class AlphaEssRuntimeData` with fields `client: AlphaEssAPI`, `systems: dict[str, EssSystem]` (later stories add coordinator fields); `type AlphaEssConfigEntry = ConfigEntry[AlphaEssRuntimeData]`; generic base `class AlphaEssCoordinator[DataT](DataUpdateCoordinator[dict[str, DataT]])` taking `hass`, `entry`, `client`, `systems`, `name`, `update_interval`, passing `config_entry=entry`; abstract `async def _async_fetch_system(self, sys_sn: str) -> DataT`; `_async_update_data` returns `{sys_sn: await self._async_fetch_system(sys_sn) for sys_sn in systems}` and maps `AlphaEssAuthError` → `ConfigEntryAuthFailed(translation_domain=DOMAIN, translation_key="authentication_failed")`, `AlphaEssConnectionError`/`AlphaEssRequestError` → `UpdateFailed(translation_domain=DOMAIN, translation_key="communication_error", translation_placeholders={"error": str(err)})`.
- [X] T010 [P] Create `custom_components/alpha_ess/entity.py`: function `system_device_info(system: EssSystem) -> DeviceInfo` returning `identifiers={(DOMAIN, system.sys_sn)}`, `manufacturer=MANUFACTURER`, `model=system.minv`, `serial_number=system.sys_sn`, `name=f"Alpha ESS {system.sys_sn}"`; class `AlphaEssCoordinatorEntity[CoordinatorT: AlphaEssCoordinator](CoordinatorEntity[CoordinatorT])` with `_attr_has_entity_name = True`, constructor `(coordinator, system, description)` setting `entity_description`, `_attr_unique_id = f"{system.sys_sn}_{description.key}"`, `_attr_device_info` and storing `self._sys_sn`.
- [X] T011 Create `tests/__init__.py` (empty) and `tests/conftest.py` with: autouse fixture enabling `enable_custom_integrations`; helper `_load_payload(name: str)` reading `tests/fixtures/{name}.json` via `pathlib` and returning its `"data"` value; fixture `ess_list_fixture` (default `"getEssList"`) and `live_fixture` (default `"getLastPowerData"`) for parametrization; fixture `mock_config_entry` returning `MockConfigEntry(domain=DOMAIN, title="Alpha ESS AL0000000000000", data={CONF_APP_ID: "test-app-id", CONF_APP_SECRET: "test-app-secret"}, unique_id="test-app-id")`; fixture `mock_setup_entry` patching `custom_components.alpha_ess.async_setup_entry` with `return_value=True`; fixture `mock_alphaess_client` patching `custom_components.alpha_ess.AlphaEssAPI` with `autospec=True` and the same mock for `custom_components.alpha_ess.config_flow.AlphaEssAPI`, whose instance returns `[EssSystem.model_validate(s) for s in payload]` from `get_ess_list`, `LastPowerData.model_validate(...)` from `get_last_power_data`, `DailyEnergy.model_validate(...)` from `get_one_date_energy_by_sn` and `SystemSummary.model_validate(...)` from `get_sum_data_for_customer`; fixture `init_integration` that adds the entry, calls `hass.config_entries.async_setup` and `hass.async_block_till_done()` and returns the entry.
- [X] T012 [P] Create `tests/test_translations.py` asserting that `custom_components/alpha_ess/translations/en.json` parses to the same dict as `custom_components/alpha_ess/strings.json`, and that every key in `strings.json` also exists in `translations/de.json` (mark the German check `xfail(strict=True)` until T037 is done, then remove the marker).

**Checkpoint**: `uv run pytest` collects, `uv run mypy` passes on the foundation

---

## Phase 3: User Story 1 - Connect the AlphaESS account and see live power flows (Priority: P1) 🎯 MVP

**Goal**: Setup via UI with AppID/AppSecret; one device per system; live power, SoC and static system sensors refreshed every 60 s.

**Independent Test**: Run `uv run pytest tests/test_config_flow.py tests/test_init.py tests/test_sensor.py` — setup succeeds, one device per system exists, live sensors match the fixture values; manually, a real account shows values matching the AlphaESS app within 60 s.

### Tests for User Story 1 (write first, must fail) ⚠️

- [X] T013 [P] [US1] In `tests/test_config_flow.py` write: `test_user_flow_creates_entry` (form → submit `app_id`/`app_secret` → `CREATE_ENTRY`, title `"Alpha ESS AL0000000000000"`, data equals input, `unique_id == "test-app-id"`, `mock_setup_entry` called once); `test_user_flow_title_with_two_systems` (`ess_list_fixture="getEssList_two_systems"` → title `"Alpha ESS"`); parametrized `test_user_flow_errors` for `AlphaEssAuthError("x", code=6007)` → `{"base": "invalid_auth"}`, `AlphaEssConnectionError` → `cannot_connect`, `AlphaEssRequestError("x", code=6001)` → `cannot_connect`, `RuntimeError` → `unknown`, each followed by a successful retry ending in `CREATE_ENTRY`; `test_user_flow_already_configured` (abort `already_configured`); `test_user_flow_no_systems` (`get_ess_list` returns `[]` → abort `no_systems`).
- [X] T014 [P] [US1] In `tests/test_init.py` write: `test_load_unload_entry` (`LOADED` → unload → `NOT_LOADED`); parametrized `test_setup_errors` — `get_ess_list` raising `AlphaEssConnectionError` → `SETUP_RETRY`, `AlphaEssAuthError` → `SETUP_ERROR`, returning `[]` → `SETUP_ERROR`; `test_device_per_system` with `ess_list_fixture="getEssList_two_systems"` asserting two devices in the device registry with identifiers `(alpha_ess, sys_sn)`, `manufacturer == "Alpha ESS"`, `model` equal to `minv`, `serial_number` equal to `sys_sn`.
- [X] T015 [P] [US1] In `tests/test_sensor.py` write: `test_live_and_system_sensors` using `entity_registry_enabled_by_default` fixture, `init_integration` and `snapshot_platform` (snapshot stored in `tests/snapshots/test_sensor.ambr`); `test_grid_import_export_power` (fixture `pgrid=3230` → `grid_import_power` 3230, `grid_export_power` 0; then `get_last_power_data` returns `pgrid=-500`, `freezer.tick(LIVE_UPDATE_INTERVAL)`, `async_fire_time_changed`, → import 0, export 500); `test_optional_sensors_not_created` (`live_fixture="getLastPowerData_minimal"` → no `ev_power`, `pv_string_*`, `pv_dc_meter_power`, `grid_power_l*`, `inverter_power_l*` entities in the registry); `test_missing_value_is_unknown` (after setup, `soc=None` on next refresh → state `unknown`, not `0`).

### Implementation for User Story 1

- [X] T016 [US1] In `custom_components/alpha_ess/coordinator.py` add `class AlphaEssLiveCoordinator(AlphaEssCoordinator[LastPowerData])` with `name=f"{DOMAIN}_live"`, `update_interval=LIVE_UPDATE_INTERVAL`, `_async_fetch_system` calling `self.client.get_last_power_data(sys_sn)`; add field `live: AlphaEssLiveCoordinator` to `AlphaEssRuntimeData`.
- [X] T017 [US1] Create `custom_components/alpha_ess/__init__.py`: `PLATFORMS = [Platform.SENSOR]`; `async_setup_entry(hass, entry: AlphaEssConfigEntry)` builds `AlphaEssAPI(AlphaEssAuth(appid=entry.data[CONF_APP_ID], appsecret=entry.data[CONF_APP_SECRET]), session=async_get_clientsession(hass))`, calls `get_ess_list()` mapping `AlphaEssAuthError` → `ConfigEntryAuthFailed`, `AlphaEssConnectionError`/`AlphaEssRequestError` → `ConfigEntryNotReady`, empty list → `ConfigEntryError(translation_domain=DOMAIN, translation_key="no_systems")` (all with translation keys); creates the live coordinator, awaits `async_config_entry_first_refresh()`, sets `entry.runtime_data`, forwards `PLATFORMS`; `async_unload_entry` unloads platforms.
- [X] T018 [US1] Create `custom_components/alpha_ess/config_flow.py` per [contracts/config-flow.md](contracts/config-flow.md) step `user`: `class AlphaEssConfigFlow(ConfigFlow, domain=DOMAIN)`, `VERSION = 1`; schema `probatio.Schema({probatio.Required(CONF_APP_ID): TextSelector(TextSelectorConfig(autocomplete="off")), probatio.Required(CONF_APP_SECRET): TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))})` wrapped in `add_suggested_values_to_schema(..., user_input)`; strip `app_id`; helper `_async_fetch_systems(app_id, app_secret) -> tuple[dict[str, str], list[EssSystem]]` mapping errors exactly as in the contract table (log `LOGGER.exception` for unknown); `async_set_unique_id(app_id)` + `_abort_if_unique_id_configured()`; abort `no_systems` for an empty list; title `f"Alpha ESS {systems[0].sys_sn}"` if exactly one system, else `"Alpha ESS"`.
- [X] T019 [US1] In `custom_components/alpha_ess/sensor.py` define `@dataclass(frozen=True, kw_only=True) class AlphaEssSensorEntityDescription[DataT](SensorEntityDescription)` with `value_fn: Callable[[DataT], StateType]` and `exists_fn: Callable[[DataT], bool] = lambda _: True`; tuple `LIVE_SENSORS` with exactly the keys, sources, device classes, units, state classes, disabled-by-default (`entity_registry_enabled_default=False`) and optional (`exists_fn` checking `is not None`) flags of the "Live sensors" table in [contracts/entities.md](contracts/entities.md), including `grid_import_power` = `max(pgrid, 0)` and `grid_export_power` = `max(-pgrid, 0)` returning `None` when `pgrid is None`; tuple `SYSTEM_SENSORS` per the "System sensors" table with `entity_category=EntityCategory.DIAGNOSTIC`; every description sets `translation_key=key`.
- [X] T020 [US1] In `custom_components/alpha_ess/sensor.py` add `PARALLEL_UPDATES = 0`, `class AlphaEssLiveSensor(AlphaEssCoordinatorEntity[AlphaEssLiveCoordinator], SensorEntity)` whose `native_value` returns `description.value_fn(self.coordinator.data[self._sys_sn])`, `class AlphaEssSystemSensor(SensorEntity)` with `_attr_has_entity_name = True`, `_attr_should_poll = False`, static `native_value` from the `EssSystem`, unique ID and device info like the coordinator entity; `async_setup_entry` creating, for every system, the live sensors whose `exists_fn(coordinator.data[sys_sn])` is true and all system sensors.
- [X] T021 [US1] Create `custom_components/alpha_ess/strings.json` with literal English texts (no `[%key:...]` references, so the file can be copied to `translations/en.json` for HACS): `config.step.user` (title, description pointing to https://open.alphaess.com/, `data` and `data_description` for `app_id` and `app_secret`), `config.error` (`invalid_auth`, `cannot_connect`, `unknown`), `config.abort` (`already_configured`, `no_systems`), `entity.sensor.<key>.name` for every live and system key, `exceptions` (`authentication_failed`, `communication_error` with `{error}`, `no_systems`).
- [X] T022 [P] [US1] Create `custom_components/alpha_ess/icons.json` with `entity.sensor` icons for sensors without a device-class icon: `pv_power` and `pv_string_*_power` and `pv_dc_meter_power` → `mdi:solar-power`, `grid_import_power` → `mdi:transmission-tower-import`, `grid_export_power` → `mdi:transmission-tower-export`, `grid_power` and `grid_power_l*` → `mdi:transmission-tower`, `load_power` → `mdi:home-lightning-bolt`, `ev_power` → `mdi:ev-station`, `battery_model` → `mdi:battery`.
- [X] T023 [US1] Copy `custom_components/alpha_ess/strings.json` to `custom_components/alpha_ess/translations/en.json`; run `uv run pytest --snapshot-update tests/test_sensor.py`, review `tests/snapshots/test_sensor.ambr` against [contracts/entities.md](contracts/entities.md), then run the full suite, `uv run mypy` and `uv run ruff check .` until all pass.

**Checkpoint**: MVP — the integration can be installed and shows live data; all US1 tests green

---

## Phase 4: User Story 2 - Track energy in the Energy dashboard (Priority: P2)

**Goal**: Daily energy, summary and self-consumption/self-sufficiency sensors from a separate 5-minute coordinator, usable in the Energy dashboard.

**Independent Test**: `uv run pytest tests/test_sensor.py -k energy` passes; in a real instance the Energy dashboard offers the sensors from the contract's mapping and daily totals match the AlphaESS app after one day (SC-003).

### Tests for User Story 2 (write first, must fail) ⚠️

- [X] T024 [P] [US2] In `tests/test_sensor.py` add: `test_energy_sensor_values` (`pv_energy_today` 9.3, `grid_import_energy_today` 11.94, `grid_export_energy_today` 0.02, `battery_charge_energy_today` 5.31, `battery_discharge_energy_today` 5.15, `battery_grid_charge_energy_today` 0.33, `load_energy_today` 15.4, `pv_energy_total` 16521.0, `self_consumption` 61.0, `self_sufficiency` 67.0 (from `0.6702 × 100` rounded to 1 decimal → 67.0), all with unit kWh or % and state class `total_increasing` for energy); `test_energy_query_date_follows_local_midnight` (set `hass.config.time_zone` to `"Europe/Berlin"`, freeze at `2026-10-18 23:58:00+02:00`, set up, `freezer.move_to("2026-10-19 00:03:00+02:00")`, fire time changed, assert last `get_one_date_energy_by_sn` call used `datetime.date(2026, 10, 19)`); `test_energy_failure_keeps_live_sensors` (energy endpoint raises `AlphaEssConnectionError`, tick `ENERGY_UPDATE_INTERVAL` → `pv_energy_today` unavailable, `pv_power` still available).

### Implementation for User Story 2

- [X] T025 [US2] In `custom_components/alpha_ess/coordinator.py` add `@dataclass(frozen=True) class SystemEnergy` with `daily: DailyEnergy` and `summary: SystemSummary`, and `class AlphaEssEnergyCoordinator(AlphaEssCoordinator[SystemEnergy])` with `name=f"{DOMAIN}_energy"`, `update_interval=ENERGY_UPDATE_INTERVAL`, `_async_fetch_system` calling `get_one_date_energy_by_sn(sys_sn, dt_util.now().date())` and `get_sum_data_for_customer(sys_sn)`; add field `energy: AlphaEssEnergyCoordinator` to `AlphaEssRuntimeData`.
- [X] T026 [US2] In `custom_components/alpha_ess/__init__.py` create the energy coordinator next to the live one and await its `async_config_entry_first_refresh()` before forwarding platforms.
- [X] T027 [US2] In `custom_components/alpha_ess/sensor.py` add tuple `ENERGY_SENSORS` exactly per the "Energy sensors" table in [contracts/entities.md](contracts/entities.md) (`self_consumption`/`self_sufficiency` value = `round(value * 100, 1)` or `None`; `ev_energy_today` optional via `exists_fn`), class `AlphaEssEnergySensor(AlphaEssCoordinatorEntity[AlphaEssEnergyCoordinator], SensorEntity)`, and create these entities in `async_setup_entry`.
- [X] T028 [US2] Add `entity.sensor.<key>.name` for all energy keys to `custom_components/alpha_ess/strings.json`, icons (`pv_energy_*` → `mdi:solar-power-variant`, `self_consumption` → `mdi:home-percent`, `self_sufficiency` → `mdi:home-battery`, `ev_energy_today` → `mdi:ev-station`) to `custom_components/alpha_ess/icons.json`, re-copy `strings.json` to `translations/en.json`, run `uv run pytest --snapshot-update tests/test_sensor.py`, review the new snapshot entries, and run the full suite, mypy and ruff.

**Checkpoint**: US1 and US2 work; Energy dashboard sources exist

---

## Phase 5: User Story 3 - Stay informed when the connection breaks and fix it in place (Priority: P3)

**Goal**: Unavailable/recover behavior, reauth and reconfigure without data loss, stale-device removal, redacted diagnostics.

**Independent Test**: `uv run pytest tests/test_config_flow.py tests/test_init.py tests/test_diagnostics.py` passes including reauth, reconfigure, recovery and stale-device cases; config flow coverage is 100 %.

### Tests for User Story 3 (write first, must fail) ⚠️

- [X] T029 [P] [US3] In `tests/test_config_flow.py` add: `test_reauth_flow` (`mock_config_entry.start_reauth_flow(hass)` → form `reauth_confirm` → submit new `app_secret` → abort `reauth_successful`, entry data has new secret and unchanged `app_id`); parametrized `test_reauth_flow_errors` (same error mapping as user step, then successful retry); `test_reconfigure_flow` (`mock_config_entry.start_reconfigure_flow(hass)` → form `reconfigure` → abort `reconfigure_successful`, new secret stored); parametrized `test_reconfigure_flow_errors`.
- [X] T030 [P] [US3] In `tests/test_init.py` add: `test_auth_error_during_polling_starts_reauth` (after setup, `get_last_power_data` raises `AlphaEssAuthError`, tick `LIVE_UPDATE_INTERVAL` → one flow in `hass.config_entries.flow.async_progress()` with `context["source"] == SOURCE_REAUTH`); `test_entities_unavailable_and_recover` (`get_last_power_data` raises `AlphaEssConnectionError` → `pv_power` state `unavailable`; restore return value, tick again → numeric state; assert "unavailable" and "back online" each logged once via `caplog`); `test_stale_device_removed` (register a device with identifiers `(alpha_ess, "AL9999999999999")` for the entry before setup → after setup it is gone, the current system's device remains).
- [X] T031 [P] [US3] Create `tests/test_diagnostics.py`: `test_entry_diagnostics` using `get_diagnostics_for_config_entry` from `pytest_homeassistant_custom_component.components.diagnostics` compared to a syrupy snapshot (exclude `created_at`, `modified_at`, `entry_id` via `props`), and assert that `json.dumps(result)` contains none of `"test-app-id"`, `"test-app-secret"`, `"AL0000000000000"`.

### Implementation for User Story 3

- [X] T032 [US3] In `custom_components/alpha_ess/config_flow.py` add `async_step_reauth(entry_data)` → `async_step_reauth_confirm`, and `async_step_reauth_confirm` / `async_step_reconfigure` per [contracts/config-flow.md](contracts/config-flow.md): password-only schema for `app_secret`, validation with the stored `app_id` via `_async_fetch_systems`, success via `async_update_reload_and_abort(entry, data_updates={CONF_APP_SECRET: ...})` using `_get_reauth_entry()` / `_get_reconfigure_entry()`.
- [X] T033 [US3] In `custom_components/alpha_ess/__init__.py`, after loading systems, remove stale devices: for each device in `dr.async_entries_for_config_entry(device_registry, entry.entry_id)` whose `(DOMAIN, sys_sn)` identifier is not in `systems`, call `device_registry.async_update_device(device.id, remove_config_entry_id=entry.entry_id)`; extract this into a module-internal helper `_remove_stale_devices`.
- [X] T034 [US3] Create `custom_components/alpha_ess/diagnostics.py` per [contracts/diagnostics-and-library.md](contracts/diagnostics-and-library.md): `async_get_config_entry_diagnostics` returning `entry` (`async_redact_data(entry.as_dict(), {CONF_APP_ID, CONF_APP_SECRET, "unique_id", "title"})`), `systems`, `live`, `energy` with every serial number replaced by `system_1`, `system_2`, … in system-list order (keys and `sys_sn` values), using `model_dump(mode="json")`.
- [X] T035 [US3] Add `config.step.reauth_confirm` and `config.step.reconfigure` (title, description, `data`/`data_description` for `app_secret`) and `config.abort.reauth_successful` / `reconfigure_successful` to `custom_components/alpha_ess/strings.json`; re-copy to `translations/en.json`; generate the diagnostics snapshot with `--snapshot-update` and review it for leaked secrets; run the full suite with `--cov=custom_components.alpha_ess --cov-report=term-missing` and confirm `config_flow.py` is at 100 %.

**Checkpoint**: All v1 user stories functional and tested

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T036 [P] Create `custom_components/alpha_ess/quality_scale.yaml` with every rule listed in `../core/homeassistant/components/fumis/quality_scale.yaml`; mark Bronze and Silver rules `done` or `exempt` with comment (actions, triggers, conditions, discovery: exempt — none/cloud only; `brands`: `todo` until icons are submitted to `home-assistant/brands` under `custom_integrations/alpha_ess`); Gold/Platinum rules as `done`, `exempt` or `todo` according to the implementation (`dynamic-devices`: `todo`, new systems appear only on reload).
- [X] T037 [P] Create `custom_components/alpha_ess/translations/de.json` with German texts for every key in `strings.json` (e.g. "Ungültige Zugangsdaten", "Verbindung fehlgeschlagen", "Netzbezug", "Netzeinspeisung", "Eigenverbrauchsquote", "Autarkiegrad"); remove the `xfail` marker from the German check in `tests/test_translations.py`.
- [X] T038 [P] Create `README.md`: purpose, prerequisites (AppID/AppSecret from https://open.alphaess.com/), HACS installation as custom repository, setup, entity list with Energy dashboard mapping (from [contracts/entities.md](contracts/entities.md)), sign conventions (grid: + import/− export; battery: as verified in T041), data update intervals (60 s / 5 min, not configurable), known limitations (read-only, new systems after reload, same time zone assumption, AlphaESS cloud only), troubleshooting (reauth, diagnostics download), removal instructions.
- [X] T039 Run all automated checks from [quickstart.md](quickstart.md) section 1 and the hassfest container from section 2; fix every finding.
- [X] T040 After `alphaess-aio` 1.0.1 is on PyPI: remove `[tool.uv.sources]` from `pyproject.toml`, run `uv lock && uv sync`, run the full test suite again.
- [ ] T041 Run the manual end-to-end check in [quickstart.md](quickstart.md) section 3 with the real system; record the observed battery power sign in `README.md` and in the `battery_power` row of `specs/001-alphaess-ha-integration/contracts/entities.md`; if the sign is opposite to the expectation, adjust nothing in code (values are passed through) but document it.
- [ ] T042 Confirm the domain `alpha_ess` with the maintainer (research R2) before tagging `v0.1.0`; then create the first GitHub release so HACS can install it.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 is independent of T002–T005; T003 needs T001's local checkout for the path source.
- **Foundational (Phase 2)**: depends on Setup; blocks all stories.
- **US1 (Phase 3)**: depends on Foundational.
- **US2 (Phase 4)**: depends on US1 (extends `coordinator.py`, `__init__.py`, `sensor.py`, `strings.json` created there).
- **US3 (Phase 5)**: depends on US1 (extends `config_flow.py`, `__init__.py`); independent of US2 except that diagnostics include energy data — if US3 is built before US2, T034 omits `energy` and T028 adds it.
- **Polish (Phase 6)**: after the desired stories; T040 waits for the PyPI release of T001.

### Within Each User Story

- Test tasks first; run them and confirm they fail.
- Coordinator → `__init__.py` → config flow → sensors → strings/icons → snapshot update.
- Story complete (all its tests green, mypy and ruff clean) before the next one.

### Parallel Opportunities

- Phase 1: T004, T005 in parallel (T001 runs in the other repository and can also run in parallel).
- Phase 2: T007, T008, T010, T012 in parallel after T006.
- US1: T013, T014, T015 in parallel; T022 in parallel with T019–T021.
- US2: T024 alone, then T025 → T026 → T027 → T028 sequentially (shared files).
- US3: T029, T030, T031 in parallel; T034 in parallel with T032/T033 (different files).
- Polish: T036, T037, T038 in parallel.

## Parallel Example: User Story 1

```bash
# Tests first, in parallel (different files):
Task: "T013 config flow tests in tests/test_config_flow.py"
Task: "T014 setup/unload/device tests in tests/test_init.py"
Task: "T015 sensor tests in tests/test_sensor.py"

# Then, while sensor descriptions are written (T019), icons in parallel:
Task: "T022 icons in custom_components/alpha_ess/icons.json"
```

## Implementation Strategy

### MVP First (User Story 1 only)

1. Phase 1 + Phase 2.
2. Phase 3 (US1) → stop and validate: tests green, install in a dev instance, compare live values with the AlphaESS app.
3. Optionally release `v0.1.0-beta` via HACS for early feedback.

### Incremental Delivery

1. US1 → live data (MVP).
2. US2 → Energy dashboard.
3. US3 → resilience, reauth/reconfigure, diagnostics (needed for the Silver target).
4. Polish → quality scale, German, README, first release `v0.1.0`.

## Notes

- Commit after each task or logical group, using Conventional Commits (`feat:`, `test:`, `docs:`, `chore:`).
- Never contact the real AlphaESS cloud from tests; never commit real AppID/AppSecret or serial numbers.
- Entity keys in [contracts/entities.md](contracts/entities.md) are stable once released.
