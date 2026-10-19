"""Base entities for the Alpha ESS integration."""

from alphaessaio.models import EssSystem
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity import EntityDescription
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN, MANUFACTURER
from .coordinator import AlphaEssCoordinator


def system_device_info(system: EssSystem) -> DeviceInfo:
    """Describe the device that represents one AlphaESS system."""
    return DeviceInfo(
        identifiers={(DOMAIN, system.sys_sn)},
        manufacturer=MANUFACTURER,
        model=system.minv,
        serial_number=system.sys_sn,
        name=f"Alpha ESS {system.sys_sn}",
    )


class AlphaEssCoordinatorEntity[DataT](CoordinatorEntity[AlphaEssCoordinator[DataT]]):
    """Entity of one system whose state comes from a coordinator."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: AlphaEssCoordinator[DataT],
        system: EssSystem,
        description: EntityDescription,
    ) -> None:
        """Initialize the entity.

        Args:
            coordinator: Coordinator that provides the data of all systems.
            system: System the entity belongs to.
            description: Description of the entity.
        """
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{system.sys_sn}_{description.key}"
        self._attr_device_info = system_device_info(system)
        self._sys_sn = system.sys_sn

    @property
    def system_data(self) -> DataT:
        """Return the latest coordinator data of this entity's system."""
        return self.coordinator.data[self._sys_sn]
