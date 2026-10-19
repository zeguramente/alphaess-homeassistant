"""Config flow for the Alpha ESS integration."""

from collections.abc import Mapping
from typing import Any, override

from alphaessaio import (
    AlphaEssAPI,
    AlphaEssAuth,
    AlphaEssAuthError,
    AlphaEssConnectionError,
    AlphaEssRequestError,
)
from alphaessaio.models import EssSystem
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import (
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
import probatio

from .const import CONF_APP_ID, CONF_APP_SECRET, DEVELOPER_PORTAL_URL, DOMAIN, LOGGER

_APP_SECRET_SELECTOR = TextSelector(TextSelectorConfig(type=TextSelectorType.PASSWORD))

_USER_SCHEMA = probatio.Schema(
    {
        probatio.Required(CONF_APP_ID): TextSelector(
            TextSelectorConfig(autocomplete="off")
        ),
        probatio.Required(CONF_APP_SECRET): _APP_SECRET_SELECTOR,
    }
)

_DESCRIPTION_PLACEHOLDERS = {"developer_portal_url": DEVELOPER_PORTAL_URL}

_APP_SECRET_SCHEMA = probatio.Schema(
    {probatio.Required(CONF_APP_SECRET): _APP_SECRET_SELECTOR}
)


class AlphaEssConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the setup of an AlphaESS account."""

    VERSION = 1

    @override
    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for the AppID and AppSecret of the developer account."""
        errors: dict[str, str] = {}

        if user_input is not None:
            app_id = user_input[CONF_APP_ID].strip()
            app_secret = user_input[CONF_APP_SECRET]
            errors, systems = await self._async_fetch_systems(app_id, app_secret)
            if not errors:
                await self.async_set_unique_id(app_id)
                self._abort_if_unique_id_configured()
                if not systems:
                    return self.async_abort(
                        reason="no_systems",
                        description_placeholders=_DESCRIPTION_PLACEHOLDERS,
                    )
                return self.async_create_entry(
                    title=_entry_title(systems),
                    data={CONF_APP_ID: app_id, CONF_APP_SECRET: app_secret},
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(_USER_SCHEMA, user_input),
            errors=errors,
            description_placeholders=_DESCRIPTION_PLACEHOLDERS,
        )

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
    ) -> ConfigFlowResult:
        """Start reauthentication after the cloud rejected the credentials."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask for a new AppSecret after the old one was rejected."""
        return await self._async_step_update_secret(
            "reauth_confirm", self._get_reauth_entry(), user_input
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user replace the AppSecret of the account."""
        return await self._async_step_update_secret(
            "reconfigure", self._get_reconfigure_entry(), user_input
        )

    async def _async_step_update_secret(
        self, step_id: str, entry: ConfigEntry, user_input: dict[str, Any] | None
    ) -> ConfigFlowResult:
        """Validate a new AppSecret with the stored AppID and reload the entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            app_secret = user_input[CONF_APP_SECRET]
            errors, _ = await self._async_fetch_systems(
                entry.data[CONF_APP_ID], app_secret
            )
            if not errors:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_APP_SECRET: app_secret}
                )

        return self.async_show_form(
            step_id=step_id,
            data_schema=_APP_SECRET_SCHEMA,
            errors=errors,
            description_placeholders=_DESCRIPTION_PLACEHOLDERS,
        )

    async def _async_fetch_systems(
        self, app_id: str, app_secret: str
    ) -> tuple[dict[str, str], list[EssSystem]]:
        """Validate the credentials by loading the systems of the account."""
        client = AlphaEssAPI(
            AlphaEssAuth(appid=app_id, appsecret=app_secret),
            session=async_get_clientsession(self.hass),
        )
        try:
            systems = await client.get_ess_list()
        except AlphaEssAuthError:
            return {"base": "invalid_auth"}, []
        except AlphaEssConnectionError, AlphaEssRequestError:
            return {"base": "cannot_connect"}, []
        except Exception:  # noqa: BLE001
            LOGGER.exception("Unexpected error while validating the credentials")
            return {"base": "unknown"}, []
        return {}, systems


def _entry_title(systems: list[EssSystem]) -> str:
    if len(systems) == 1:
        return f"Alpha ESS {systems[0].sys_sn}"
    return "Alpha ESS"
