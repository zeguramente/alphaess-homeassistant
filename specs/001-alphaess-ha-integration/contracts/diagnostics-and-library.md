# Contract: Diagnostics and Library Usage

## Config entry diagnostics

Downloadable from the integration page. Structure:

```text
{
  "entry":   config entry as dict, with data.app_id and data.app_secret redacted,
  "systems": [EssSystem.model_dump() per system],
  "live":    {sys_sn: LastPowerData.model_dump()},
  "energy":  {sys_sn: {"daily": DailyEnergy..., "summary": SystemSummary...}}
}
```

Redacted with `async_redact_data`: `app_id`, `app_secret`, `unique_id`, `title`, `sys_sn` and
every dictionary key that is a serial number (replaced by `system_1`, `system_2`, … in list
order). Verified by a snapshot test (FR-016).

## Library usage (`alphaess-aio`)

The integration uses only this public interface. Anything else needed is added to the library
first (Constitution I).

| Used | Where |
|---|---|
| `AlphaEssAuth(appid, appsecret)` | config flow, setup |
| `AlphaEssAPI(auth, session=async_get_clientsession(hass))` | config flow, setup |
| `get_ess_list() -> list[EssSystem]` | config flow validation, setup |
| `get_last_power_data(sys_sn) -> LastPowerData` | live coordinator |
| `get_one_date_energy_by_sn(sys_sn, date) -> DailyEnergy` | energy coordinator |
| `get_sum_data_for_customer(sys_sn) -> SystemSummary` | energy coordinator |
| `AlphaEssAuthError`, `AlphaEssConnectionError`, `AlphaEssRequestError`, `AlphaEssError` | error mapping |

Requirement in `manifest.json`: `alphaess-aio==1.0.1` (adds `py.typed`, see research R3).
`loggers`: `["alphaessaio"]`.
