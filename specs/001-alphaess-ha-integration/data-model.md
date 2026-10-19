# Data Model: AlphaESS Home Assistant Integration

**Feature**: [spec.md](spec.md) | **Research**: [research.md](research.md)

The integration stores no data of its own beyond the config entry. All other structures live in
memory and are rebuilt on every setup. Library models (`alphaessaio.models`) are used as-is.

## Config entry (persisted by Home Assistant)

| Field | Type | Rules |
|---|---|---|
| `unique_id` | str | = AppID; at most one entry per AppID (FR-003) |
| `title` | str | "Alpha ESS {sys_sn}" if the account has one system, else "Alpha ESS" |
| `data.app_id` | str | non-empty, stripped; immutable after creation |
| `data.app_secret` | str | non-empty; updated by reauth/reconfigure; never logged (FR-019) |
| `version` / `minor_version` | int | 1 / 1 |

No options flow (polling interval is fixed, Constitution IV).

## Runtime data (`AlphaEssConfigEntry.runtime_data`)

`AlphaEssRuntimeData` (dataclass):

| Field | Type | Source |
|---|---|---|
| `systems` | `dict[str, EssSystem]` keyed by `sys_sn` | `get_ess_list()` once at setup |
| `live` | `AlphaEssLiveCoordinator` | — |
| `energy` | `AlphaEssEnergyCoordinator` | — |

Setup fails with `ConfigEntryAuthFailed` on `AlphaEssAuthError`, `ConfigEntryNotReady` on
`AlphaEssConnectionError` / `AlphaEssRequestError`, and `ConfigEntryError` (translated) if the
account has no systems any more.

## Coordinator data

### Live coordinator — `dict[str, LastPowerData]`

- Key: `sys_sn` for every system in `runtime_data.systems`.
- Interval: 60 s.
- Any error for any system → `UpdateFailed` (whole update failed, entities unavailable, FR-014);
  `AlphaEssAuthError` → `ConfigEntryAuthFailed` (FR-015).

### Energy coordinator — `dict[str, SystemEnergy]`

`SystemEnergy` (frozen dataclass):

| Field | Type | Source |
|---|---|---|
| `daily` | `DailyEnergy` | `get_one_date_energy_by_sn(sys_sn, today)` |
| `summary` | `SystemSummary` | `get_sum_data_for_customer(sys_sn)` |

- `today` = current date in Home Assistant's time zone at the start of the update.
- Interval: 5 min. Error handling as for the live coordinator.

## Entity description

`AlphaEssSensorEntityDescription(SensorEntityDescription)` adds:

| Field | Type | Meaning |
|---|---|---|
| `value_fn` | `Callable[[T], StateType]` | extracts the value from the coordinator data of one system |
| `exists_fn` | `Callable[[T], bool]` | default `lambda _: True`; optional sensors check for `None` at setup (research R9) |

Three description groups, one per data source: live (`LastPowerData`), energy
(`SystemEnergy`), system (`EssSystem`, static). The full catalogue with keys, units and classes is
in [contracts/entities.md](contracts/entities.md).

## Identity rules

- Device identifier: `(alpha_ess, sys_sn)`.
- Entity unique ID: `{sys_sn}_{description.key}`; keys are stable once released.
- Stale device: a device of this entry whose `sys_sn` is not in `runtime_data.systems` is removed
  at setup.

## Value transformations

| Value | Transformation |
|---|---|
| `eself_consumption`, `eself_sufficiency` | × 100, rounded to 1 decimal |
| grid import power | `max(pgrid, 0)`; `None` if `pgrid` is `None` |
| grid export power | `max(-pgrid, 0)`; `None` if `pgrid` is `None` |
| any `None` from the API | state `unknown`, never `0` |

## State transitions

```text
config entry:  not loaded ──setup ok──▶ loaded ──auth error──▶ setup error (reauth pending)
                    │                     │  ▲                         │
                    └─cloud down─▶ setup retry │ └────reauth ok/reload──┘
entity:        available ◀──update ok── unavailable ◀──update failed──
```
