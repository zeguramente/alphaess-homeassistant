# Alpha ESS for Home Assistant

Brings the live power flows, daily energy and system data of
[AlphaESS](https://www.alphaess.com/) energy storage systems into Home Assistant,
using the official [AlphaESS Open API](https://open.alphaess.com/) through the
[`alphaess-aio`](https://github.com/zeguramente/alphaess-aio) library.

The integration is read-only: it shows data but does not change any settings of
your system.

## Use cases

- See PV, house, grid and battery power on a dashboard, updated every minute.
- Track solar production, grid import/export and battery charge/discharge in the
  Home Assistant **Energy dashboard**.
- Automate on the battery state of charge or on grid export, for example start the
  dishwasher when more than 2 kW are fed into the grid.

## Prerequisites

- An AlphaESS system that is visible in the AlphaESS app.
- An AlphaESS developer account at <https://open.alphaess.com/> with your system
  bound to it. After registering, the portal shows your **AppID** and **AppSecret**.
- Home Assistant 2026.10 or newer.

## Installation (HACS)

1. In HACS, open the menu → **Custom repositories**, add
   `https://github.com/zeguramente/alphaess-homeassistant` with category
   **Integration**.
2. Search for "Alpha ESS" in HACS and download it.
3. Restart Home Assistant.

Manual installation: copy `custom_components/alpha_ess` into the
`custom_components` folder of your Home Assistant configuration and restart.

## Setup

**Settings → Devices & services → Add integration → Alpha ESS**, then enter:

| Field | Description |
|---|---|
| AppID | Developer ID shown in the AlphaESS developer portal. |
| AppSecret | Developer secret shown in the AlphaESS developer portal. |

Every system bound to the account becomes a device named "Alpha ESS *serial
number*". Each AppID can be added once.

To change the AppSecret later, open the integration and choose **Reconfigure**.

## Supported devices

All AlphaESS systems (for example SMILE series inverters with SMILE batteries) that
can be bound to the AlphaESS Open API. Values a system does not report, such as an
EV charger or per-phase power, are not created as entities.

## Entities

### Live power (updated every 60 s)

| Entity | Unit | Notes |
|---|---|---|
| PV power | W | |
| Load power | W | |
| Grid power | W | positive = import, negative = export |
| Grid import power | W | grid power when importing, otherwise 0 |
| Grid export power | W | grid power when exporting, otherwise 0 |
| Battery power | W | sign as reported by AlphaESS, see below |
| Battery state of charge | % | |
| EV charger power | W | only if an EV charger is reported |
| PV string 1–4 power, PV DC meter power | W | disabled by default |
| Grid power L1–L3 | W | disabled by default |
| Inverter power L1–L3 | W | disabled by default |

### Energy (updated every 5 min)

| Entity | Unit | Notes |
|---|---|---|
| PV energy today | kWh | resets at midnight |
| Grid import energy today | kWh | resets at midnight |
| Grid export energy today | kWh | resets at midnight |
| Battery charge energy today | kWh | resets at midnight |
| Battery discharge energy today | kWh | resets at midnight |
| Battery grid charge energy today | kWh | resets at midnight |
| EV charger energy today | kWh | only if reported |
| Load energy today | kWh | resets at midnight |
| PV energy total | kWh | lifetime |
| Self-consumption | % | share of PV energy used on site |
| Self-sufficiency | % | share of consumption covered without the grid |

### System (diagnostic, read at setup)

Battery capacity (kWh), battery usable capacity (%), inverter nominal power (kW),
PV nominal power (kW, i.e. kWp) and battery model.

### Energy dashboard

| Energy dashboard setting | Entity |
|---|---|
| Solar production | PV energy today |
| Grid consumption | Grid import energy today |
| Return to grid | Grid export energy today |
| Battery: energy going in | Battery charge energy today |
| Battery: energy coming out | Battery discharge energy today |

### Sign conventions

- **Grid power**: positive while importing from the grid, negative while exporting.
- **Battery power**: passed through unchanged from AlphaESS. Positive values are
  expected to mean discharging; this has not been verified against a real system
  yet.

## Data updates

Live power is fetched every 60 seconds, energy and summary data every 5 minutes.
The intervals are fixed to respect the rate limits of the AlphaESS cloud. A value
the cloud does not deliver is shown as *unknown*, never as 0.

## Example

```yaml
automation:
  - alias: "Start dishwasher on solar surplus"
    triggers:
      - trigger: numeric_state
        entity_id: sensor.alpha_ess_al0000000000000_grid_export_power
        above: 2000
        for: "00:05:00"
    actions:
      - action: switch.turn_on
        target:
          entity_id: switch.dishwasher
```

Replace the serial number in the entity ID with the one of your system.

## Known limitations

- Read-only: battery charge/discharge settings and EV charger control are not
  supported yet.
- Systems bound to the account after setup appear only after reloading the
  integration; systems that were unbound are removed on reload.
- Daily values assume that the AlphaESS system and Home Assistant use the same time
  zone.
- Cloud only: the integration needs the AlphaESS cloud; there is no local
  connection to the inverter.

## Troubleshooting

- **Entities are unavailable**: the AlphaESS cloud could not be reached. The
  entities recover automatically with the next successful update; the log contains
  one message when the connection is lost and one when it is back.
- **"Re-authentication required"**: the cloud rejected the AppSecret. Open the
  notification and enter the current AppSecret from the developer portal.
- **Diagnostics**: on the integration page, open the menu of the entry and choose
  **Download diagnostics**. AppID, AppSecret and serial numbers are removed from the
  file, so it can be attached to an issue.

## Removal

1. **Settings → Devices & services → Alpha ESS**, open the menu of the entry and
   choose **Delete**.
2. Optionally remove the integration in HACS and restart Home Assistant.
3. Optionally unbind the system or delete the developer account at
   <https://open.alphaess.com/>.
