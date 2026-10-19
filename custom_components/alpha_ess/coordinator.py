"""Data update coordinators for the Alpha ESS integration."""

from abc import abstractmethod
from dataclasses import dataclass
from datetime import timedelta
from typing import override

from alphaessaio import (
    AlphaEssAPI,
    AlphaEssAuthError,
    AlphaEssConnectionError,
    AlphaEssRequestError,
)
from alphaessaio.models import DailyEnergy, EssSystem, LastPowerData, SystemSummary
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .const import DOMAIN, ENERGY_UPDATE_INTERVAL, LIVE_UPDATE_INTERVAL, LOGGER


@dataclass
class AlphaEssRuntimeData:
    """Objects shared by all platforms of one config entry.

    Attributes:
        client: Client of the AlphaESS account.
        systems: Systems of the account at setup, keyed by serial number.
        live: Coordinator of the real-time power data.
        energy: Coordinator of the daily energy and summary data.
    """

    client: AlphaEssAPI
    systems: dict[str, EssSystem]
    live: AlphaEssLiveCoordinator
    energy: AlphaEssEnergyCoordinator


@dataclass(frozen=True)
class SystemEnergy:
    """Energy figures of one system.

    Attributes:
        daily: Energy totals of the current day.
        summary: Aggregated energy figures.
    """

    daily: DailyEnergy
    summary: SystemSummary


type AlphaEssConfigEntry = ConfigEntry[AlphaEssRuntimeData]


class AlphaEssCoordinator[DataT](DataUpdateCoordinator[dict[str, DataT]]):
    """Fetch one kind of data for every system of the account.

    A failure for any system fails the whole update, so all entities of this
    coordinator become unavailable together.
    """

    config_entry: AlphaEssConfigEntry

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AlphaEssConfigEntry,
        client: AlphaEssAPI,
        systems: dict[str, EssSystem],
        *,
        name: str,
        update_interval: timedelta,
    ) -> None:
        """Initialize the coordinator.

        Args:
            hass: Home Assistant instance.
            entry: Config entry the coordinator belongs to.
            client: Client of the AlphaESS account.
            systems: Systems to fetch data for, keyed by serial number.
            name: Name used in log messages.
            update_interval: Time between two updates.
        """
        super().__init__(
            hass,
            LOGGER,
            config_entry=entry,
            name=name,
            update_interval=update_interval,
        )
        self.client = client
        self.systems = systems

    @abstractmethod
    async def _async_fetch_system(self, sys_sn: str) -> DataT:
        """Fetch the data of one system."""

    @override
    async def _async_update_data(self) -> dict[str, DataT]:
        """Fetch the data of all systems."""
        try:
            return {
                sys_sn: await self._async_fetch_system(sys_sn)
                for sys_sn in self.systems
            }
        except AlphaEssAuthError as err:
            raise ConfigEntryAuthFailed(
                translation_domain=DOMAIN,
                translation_key="authentication_failed",
            ) from err
        except (AlphaEssConnectionError, AlphaEssRequestError) as err:
            raise UpdateFailed(
                translation_domain=DOMAIN,
                translation_key="communication_error",
                translation_placeholders={"error": str(err)},
            ) from err


class AlphaEssLiveCoordinator(AlphaEssCoordinator[LastPowerData]):
    """Fetch the real-time power data of every system."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AlphaEssConfigEntry,
        client: AlphaEssAPI,
        systems: dict[str, EssSystem],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            entry,
            client,
            systems,
            name=f"{DOMAIN}_live",
            update_interval=LIVE_UPDATE_INTERVAL,
        )

    @override
    async def _async_fetch_system(self, sys_sn: str) -> LastPowerData:
        return await self.client.get_last_power_data(sys_sn)


class AlphaEssEnergyCoordinator(AlphaEssCoordinator[SystemEnergy]):
    """Fetch the daily energy and summary data of every system."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: AlphaEssConfigEntry,
        client: AlphaEssAPI,
        systems: dict[str, EssSystem],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            entry,
            client,
            systems,
            name=f"{DOMAIN}_energy",
            update_interval=ENERGY_UPDATE_INTERVAL,
        )

    @override
    async def _async_fetch_system(self, sys_sn: str) -> SystemEnergy:
        return SystemEnergy(
            daily=await self.client.get_one_date_energy_by_sn(
                sys_sn, dt_util.now().date()
            ),
            summary=await self.client.get_sum_data_for_customer(sys_sn),
        )
