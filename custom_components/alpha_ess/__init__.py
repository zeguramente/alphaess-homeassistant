"""The Alpha ESS integration."""

from alphaessaio import (
    AlphaEssAPI,
    AlphaEssAuth,
    AlphaEssAuthError,
    AlphaEssConnectionError,
    AlphaEssRequestError,
)
from alphaessaio.models import EssSystem
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryError,
    ConfigEntryNotReady,
)
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import CONF_APP_ID, CONF_APP_SECRET, DOMAIN
from .coordinator import (
    AlphaEssConfigEntry,
    AlphaEssEnergyCoordinator,
    AlphaEssLiveCoordinator,
    AlphaEssRuntimeData,
)

PLATFORMS = [Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, entry: AlphaEssConfigEntry) -> bool:
    """Set up Alpha ESS from a config entry."""
    client = AlphaEssAPI(
        AlphaEssAuth(
            appid=entry.data[CONF_APP_ID], appsecret=entry.data[CONF_APP_SECRET]
        ),
        session=async_get_clientsession(hass),
    )
    systems = {system.sys_sn: system for system in await _async_load_systems(client)}
    _remove_stale_devices(hass, entry, systems)

    live = AlphaEssLiveCoordinator(hass, entry, client, systems)
    await live.async_config_entry_first_refresh()
    energy = AlphaEssEnergyCoordinator(hass, entry, client, systems)
    await energy.async_config_entry_first_refresh()

    entry.runtime_data = AlphaEssRuntimeData(
        client=client, systems=systems, live=live, energy=energy
    )
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: AlphaEssConfigEntry) -> bool:
    """Unload an Alpha ESS config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)


async def _async_load_systems(client: AlphaEssAPI) -> list[EssSystem]:
    try:
        systems = await client.get_ess_list()
    except AlphaEssAuthError as err:
        raise ConfigEntryAuthFailed(
            translation_domain=DOMAIN, translation_key="authentication_failed"
        ) from err
    except (AlphaEssConnectionError, AlphaEssRequestError) as err:
        raise ConfigEntryNotReady(
            translation_domain=DOMAIN,
            translation_key="communication_error",
            translation_placeholders={"error": str(err)},
        ) from err
    if not systems:
        raise ConfigEntryError(translation_domain=DOMAIN, translation_key="no_systems")
    return systems


def _remove_stale_devices(
    hass: HomeAssistant, entry: AlphaEssConfigEntry, systems: dict[str, EssSystem]
) -> None:
    """Remove the devices of systems that are no longer bound to the account."""
    device_registry = dr.async_get(hass)
    for device in dr.async_entries_for_config_entry(device_registry, entry.entry_id):
        serial_numbers = {
            identifier for domain, identifier in device.identifiers if domain == DOMAIN
        }
        if serial_numbers.isdisjoint(systems):
            device_registry.async_remove_device(device.id)
