# Contract: Config Flow

User-facing setup dialog of the `alpha_ess` integration. Field keys and error/abort keys are
translation keys in `strings.json` and are stable.

## Step `user`

| Field | Key | Selector | Required |
|---|---|---|---|
| AppID | `app_id` | text | yes |
| AppSecret | `app_secret` | text, type password | yes |

Validation: create a client with Home Assistant's shared session and call `get_ess_list()`.

| Outcome | Result |
|---|---|
| systems returned, AppID not configured | create entry (title see [data-model.md](../data-model.md)) |
| AppID already configured | abort `already_configured` |
| empty system list | abort `no_systems` (description points to the AlphaESS developer portal) |
| `AlphaEssAuthError` | form error `invalid_auth` |
| `AlphaEssConnectionError` | form error `cannot_connect` |
| `AlphaEssRequestError` (other) | form error `cannot_connect` |
| any other exception | form error `unknown`, logged with traceback |

Entered values are kept as suggested values when the form is shown again with an error.

## Step `reauth_confirm`

Started by Home Assistant when the coordinator raises `ConfigEntryAuthFailed`.

| Field | Key | Selector |
|---|---|---|
| AppSecret | `app_secret` | text, type password |

Validates with the stored AppID and the new secret. Success → `async_update_reload_and_abort`
with reason `reauth_successful`. Errors as in `user`.

## Step `reconfigure`

Same form and validation as `reauth_confirm`. Success → abort `reconfigure_successful`.

## Translations

English (`strings.json` → `translations/en.json`) and German (`translations/de.json`) for: step
titles and descriptions, field labels and `data_description`, errors `invalid_auth`,
`cannot_connect`, `unknown`, aborts `already_configured`, `no_systems`, `reauth_successful`,
`reconfigure_successful`, and exception messages `authentication_failed`,
`communication_error`, `no_systems`.
