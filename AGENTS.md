# alphaess-homeassistant - Agent Instructions

## Project Context
- Home Assistant custom integration for AlphaESS systems, installed through HACS. Integration: `custom_components/alpha_ess/`; tests: `tests/`.
- The API client is the library in `../alphaess-aio/` (`alphaessaio`).
- Reference for current Home Assistant patterns: `../core/homeassistant/components/fumis/` and its tests in `../core/tests/components/fumis/`.
- The constitution (`.specify/memory/constitution.md`) takes precedence over this file; read it before planning larger changes. Design docs live in `specs/`.

## Key Conventions
- Import the library only through its public API: `alphaessaio` (`AlphaEssAPI`, `AlphaEssAuth`, `AlphaEssAuthError`, `AlphaEssConnectionError`, `AlphaEssRequestError`, `AlphaEssError`) and `alphaessaio.models` (`EssSystem`, `LastPowerData`, `DailyEnergy`, `SystemSummary`).
- Catch `AlphaEssAuthError` before `AlphaEssRequestError` (it is a subclass).
- Form schemas use `probatio`, not `voluptuous`, as in fumis `config_flow.py`.
- Mark overridden methods with `typing.override`.
- Entity keys in `specs/001-alphaess-ha-integration/contracts/entities.md` are stable once released.
- Commits use Conventional Commits (`feat:`, `test:`, `docs:`, `chore:`).

## Testing
- Test helpers come from `pytest_homeassistant_custom_component.common` (in core: `tests.common`), e.g. `MockConfigEntry`, `snapshot_platform`, `async_fire_time_changed`.
- Never contact the real AlphaESS cloud from tests; never commit a real AppID, AppSecret or serial number.
- Snapshots: `uv run pytest --snapshot-update tests/test_sensor.py`.

## Commands
- `uv run pytest` (coverage: `uv run pytest --cov=custom_components.alpha_ess --cov-fail-under=95`)
- `uv run ruff check . && uv run ruff format --check .`
- `uv run mypy`
