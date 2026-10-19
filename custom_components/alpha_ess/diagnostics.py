"""Diagnostics for the Alpha ESS integration."""

from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant
from pydantic import BaseModel

from .const import CONF_APP_ID, CONF_APP_SECRET
from .coordinator import AlphaEssConfigEntry

_ENTRY_FIELDS_TO_REDACT = {CONF_APP_ID, CONF_APP_SECRET, "unique_id", "title"}


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, entry: AlphaEssConfigEntry
) -> dict[str, Any]:
    """Return the config entry and the latest data with serial numbers replaced."""
    runtime_data = entry.runtime_data
    aliases = {
        sys_sn: f"system_{number}"
        for number, sys_sn in enumerate(runtime_data.systems, start=1)
    }
    return {
        "entry": async_redact_data(entry.as_dict(), _ENTRY_FIELDS_TO_REDACT),
        "systems": [
            _dump_without_serial(system, aliases)
            for system in runtime_data.systems.values()
        ],
        "live": {
            aliases[sys_sn]: _dump_without_serial(live_data, aliases)
            for sys_sn, live_data in runtime_data.live.data.items()
        },
        "energy": {
            aliases[sys_sn]: {
                "daily": _dump_without_serial(energy.daily, aliases),
                "summary": _dump_without_serial(energy.summary, aliases),
            }
            for sys_sn, energy in runtime_data.energy.data.items()
        },
    }


def _dump_without_serial(model: BaseModel, aliases: dict[str, str]) -> dict[str, Any]:
    dumped = model.model_dump(mode="json")
    if "sys_sn" in dumped:
        dumped["sys_sn"] = aliases.get(dumped["sys_sn"], "**REDACTED**")
    return dumped
