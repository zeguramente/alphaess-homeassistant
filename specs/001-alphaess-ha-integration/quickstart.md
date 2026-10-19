# Quickstart: Validate the AlphaESS Integration

How to prove that the feature works. Contracts: [config flow](contracts/config-flow.md),
[entities](contracts/entities.md), [diagnostics](contracts/diagnostics-and-library.md).

## Prerequisites

- `uv` and Python 3.14.2 (`uv python install 3.14.2`).
- For manual checks: AppID/AppSecret from <https://open.alphaess.com/> with at least one bound
  system, and a Home Assistant 2026.10 dev instance.
- `alphaess-aio` 1.0.1 released (or the local `../alphaess-aio` checkout as path source).

## 1. Automated checks (no cloud access)

```bash
uv sync
uv run ruff check . && uv run ruff format --check .
uv run mypy custom_components/alpha_ess
uv run pytest --cov=custom_components.alpha_ess --cov-report=term-missing
```

Expected: all pass; `config_flow.py` at 100 % coverage; overall coverage ≥ 95 % (Silver
`test-coverage`).

| Scenario | Covered by | Spec |
|---|---|---|
| Setup succeeds, one device per system, entity snapshot matches | `test_sensor.py`, `test_init.py` | Story 1 / 1–2 |
| invalid_auth, cannot_connect, unknown, already_configured, no_systems | `test_config_flow.py` | Story 1 / 3–5, SC-006 |
| Cloud error → entities unavailable → recover | `test_sensor.py` (freezer + coordinator tick) | Story 3 / 1, SC-004 |
| Auth error during polling → reauth flow started, reauth succeeds | `test_init.py`, `test_config_flow.py` | Story 3 / 2–3 |
| Daily counter reset at midnight | `test_sensor.py` (date change with freezer) | Story 2 / 2 |
| Rates shown as 0–100 %, missing values unknown | `test_sensor.py` | Edge cases |
| Unbound system removed | `test_init.py` | Story 3 / 5 |
| Diagnostics redacted | `test_diagnostics.py` (snapshot) | Story 3 / 4 |

## 2. Home Assistant validation

```bash
docker run --rm -v "$PWD/custom_components:/github/workspace/custom_components" \
    ghcr.io/home-assistant/hassfest
```

Expected: no errors. The HACS action (`hacs/action`, category `integration`) runs in CI.

## 3. Manual end-to-end check with a real system

1. Copy `custom_components/alpha_ess` into the dev instance's `config/custom_components/` and
   restart.
2. Settings → Devices & services → Add integration → "Alpha ESS"; enter AppID/AppSecret.
   Expected: setup within seconds, device "Alpha ESS {serial}" (SC-001: < 2 min overall).
3. Compare PV, load, grid, battery power and SoC with the AlphaESS app. Expected: differences
   explained by ≤ 60 s staleness (SC-002). Note the battery sign and record it in the README.
4. Energy dashboard → add the sources listed in [entities.md](contracts/entities.md). After one
   day, compare totals with the app (SC-003).
5. Disconnect the network for 3 minutes. Expected: entities unavailable, then available again
   within 60 s after reconnecting (SC-004).
6. Stop Home Assistant, change `app_secret` of the entry in `.storage/core.config_entries` to a
   wrong value, start again. Expected: reauth notification; entering the correct secret restores
   entities with history (SC-005).
7. Download diagnostics. Expected: no AppID, AppSecret or serial number in the file.
