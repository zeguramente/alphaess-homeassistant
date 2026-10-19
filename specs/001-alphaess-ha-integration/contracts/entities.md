# Contract: Entities

All entities belong to the `sensor` platform and to the device of one system. Entity IDs follow
from `has_entity_name` + `translation_key`; unique IDs are `{sys_sn}_{key}`. Keys are part of the
contract: renaming a key after release breaks users' history and dashboards.

Legend — **SC**: state class (`m` = measurement, `ti` = total_increasing);
**Off**: disabled by default; **Opt**: created only when the value is not `None` at setup.

## Live sensors (every 60 s)

| Key | Source (`LastPowerData`) | Device class | Unit | SC | Off | Opt |
|---|---|---|---|---|---|---|
| `pv_power` | `ppv` | power | W | m | | |
| `load_power` | `pload` | power | W | m | | |
| `grid_power` | `pgrid` (+ import / − export) | power | W | m | | |
| `grid_import_power` | `max(pgrid, 0)` | power | W | m | | |
| `grid_export_power` | `max(-pgrid, 0)` | power | W | m | | |
| `battery_power` | `pbat` (sign verified in implementation) | power | W | m | | |
| `battery_state_of_charge` | `soc` | battery | % | m | | |
| `ev_power` | `pev` | power | W | m | | ✓ |
| `pv_string_1_power` … `pv_string_4_power` | `ppv_detail.ppv1…4` | power | W | m | ✓ | ✓ |
| `pv_dc_meter_power` | `ppv_detail.pmeter_dc` | power | W | m | ✓ | ✓ |
| `grid_power_l1` … `grid_power_l3` | `pgrid_detail.pmeter_l1…3` | power | W | m | ✓ | ✓ |
| `inverter_power_l1` … `inverter_power_l3` | `preal_l1…3` | power | W | m | ✓ | ✓ |

## Energy sensors (every 5 min)

| Key | Source (`SystemEnergy`) | Device class | Unit | SC | Off | Opt |
|---|---|---|---|---|---|---|
| `pv_energy_today` | `daily.epv` | energy | kWh | ti | | |
| `grid_import_energy_today` | `daily.e_input` | energy | kWh | ti | | |
| `grid_export_energy_today` | `daily.e_output` | energy | kWh | ti | | |
| `battery_charge_energy_today` | `daily.e_charge` | energy | kWh | ti | | |
| `battery_discharge_energy_today` | `daily.e_discharge` | energy | kWh | ti | | |
| `battery_grid_charge_energy_today` | `daily.e_grid_charge` | energy | kWh | ti | | |
| `ev_energy_today` | `daily.e_charging_pile` | energy | kWh | ti | | ✓ |
| `load_energy_today` | `summary.eload` | energy | kWh | ti | | |
| `pv_energy_total` | `summary.epvtotal` | energy | kWh | ti | | |
| `self_consumption` | `summary.eself_consumption × 100` | — | % | m | | |
| `self_sufficiency` | `summary.eself_sufficiency × 100` | — | % | m | | |

Energy dashboard mapping: solar = `pv_energy_today`; grid consumption =
`grid_import_energy_today`; return to grid = `grid_export_energy_today`; battery in/out =
`battery_charge_energy_today` / `battery_discharge_energy_today`.

## System sensors (static, entity category `diagnostic`)

Values from `get_ess_list()` at setup; updated on reload only.

| Key | Source (`EssSystem`) | Device class | Unit |
|---|---|---|---|
| `battery_capacity` | `cobat` | energy_storage | kWh |
| `battery_usable_capacity` | `us_capacity` | — | % |
| `inverter_nominal_power` | `poinv` | power | kW |
| `pv_nominal_power` | `popv` | power | kW |
| `battery_model` | `mbat` | — (text) | — |

## Not exposed in v1

Income (`today_income`, `total_income`, `money_type`), tree and CO2 equivalents,
`surplus_cobat`, `ems_status` (would be stale between reloads), the intraday power curve, and all
write operations (deferred feature).

## Availability

- Live sensors depend only on the live coordinator, energy sensors only on the energy
  coordinator; system sensors are always available while the entry is loaded.
- A failed update makes all entities of that coordinator unavailable; the first successful update
  restores them (FR-014). Unavailability and recovery are logged once each.
