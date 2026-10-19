"""Sensors for the Alpha ESS integration."""

from collections.abc import Callable
from dataclasses import dataclass
from typing import override

from alphaessaio.models import EssSystem, GridPowerDetail, LastPowerData, PvPowerDetail
from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.const import PERCENTAGE, EntityCategory, UnitOfEnergy, UnitOfPower
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.typing import StateType

from .coordinator import AlphaEssConfigEntry, SystemEnergy
from .entity import AlphaEssCoordinatorEntity, system_device_info

PARALLEL_UPDATES = 0


@dataclass(frozen=True, kw_only=True)
class AlphaEssSensorEntityDescription[DataT](SensorEntityDescription):
    """Describes an Alpha ESS sensor.

    Attributes:
        value_fn: Extracts the state from the data of one system.
        exists_fn: Decides at setup whether the system reports this value at all.
    """

    value_fn: Callable[[DataT], StateType]
    exists_fn: Callable[[DataT], bool] = lambda _: True


def _pv_detail(data: LastPowerData) -> PvPowerDetail:
    return data.ppv_detail or PvPowerDetail()


def _grid_detail(data: LastPowerData) -> GridPowerDetail:
    return data.pgrid_detail or GridPowerDetail()


def _grid_import_power(data: LastPowerData) -> float | None:
    return None if data.pgrid is None else max(data.pgrid, 0.0)


def _grid_export_power(data: LastPowerData) -> float | None:
    return None if data.pgrid is None else max(-data.pgrid, 0.0)


def _live_power_description(
    key: str,
    value_fn: Callable[[LastPowerData], float | None],
    *,
    is_optional: bool = False,
    is_enabled_by_default: bool = True,
) -> AlphaEssSensorEntityDescription[LastPowerData]:
    return AlphaEssSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.WATT,
        state_class=SensorStateClass.MEASUREMENT,
        entity_registry_enabled_default=is_enabled_by_default,
        value_fn=value_fn,
        exists_fn=(
            (lambda data: value_fn(data) is not None)
            if is_optional
            else (lambda _: True)
        ),
    )


def _live_detail_description(
    key: str, value_fn: Callable[[LastPowerData], float | None]
) -> AlphaEssSensorEntityDescription[LastPowerData]:
    return _live_power_description(
        key, value_fn, is_optional=True, is_enabled_by_default=False
    )


LIVE_SENSORS: tuple[AlphaEssSensorEntityDescription[LastPowerData], ...] = (
    _live_power_description("pv_power", lambda data: data.ppv),
    _live_power_description("load_power", lambda data: data.pload),
    _live_power_description("grid_power", lambda data: data.pgrid),
    _live_power_description("grid_import_power", _grid_import_power),
    _live_power_description("grid_export_power", _grid_export_power),
    _live_power_description("battery_power", lambda data: data.pbat),
    AlphaEssSensorEntityDescription(
        key="battery_state_of_charge",
        translation_key="battery_state_of_charge",
        device_class=SensorDeviceClass.BATTERY,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: data.soc,
    ),
    _live_power_description("ev_power", lambda data: data.pev, is_optional=True),
    _live_detail_description("pv_string_1_power", lambda data: _pv_detail(data).ppv1),
    _live_detail_description("pv_string_2_power", lambda data: _pv_detail(data).ppv2),
    _live_detail_description("pv_string_3_power", lambda data: _pv_detail(data).ppv3),
    _live_detail_description("pv_string_4_power", lambda data: _pv_detail(data).ppv4),
    _live_detail_description(
        "pv_dc_meter_power", lambda data: _pv_detail(data).pmeter_dc
    ),
    _live_detail_description(
        "grid_power_l1", lambda data: _grid_detail(data).pmeter_l1
    ),
    _live_detail_description(
        "grid_power_l2", lambda data: _grid_detail(data).pmeter_l2
    ),
    _live_detail_description(
        "grid_power_l3", lambda data: _grid_detail(data).pmeter_l3
    ),
    _live_detail_description("inverter_power_l1", lambda data: data.preal_l1),
    _live_detail_description("inverter_power_l2", lambda data: data.preal_l2),
    _live_detail_description("inverter_power_l3", lambda data: data.preal_l3),
)


def _percentage(fraction: float | None) -> float | None:
    return None if fraction is None else round(fraction * 100, 1)


def _energy_description(
    key: str,
    value_fn: Callable[[SystemEnergy], float | None],
    *,
    is_optional: bool = False,
) -> AlphaEssSensorEntityDescription[SystemEnergy]:
    return AlphaEssSensorEntityDescription(
        key=key,
        translation_key=key,
        device_class=SensorDeviceClass.ENERGY,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        state_class=SensorStateClass.TOTAL_INCREASING,
        value_fn=value_fn,
        exists_fn=(
            (lambda data: value_fn(data) is not None)
            if is_optional
            else (lambda _: True)
        ),
    )


def _rate_description(
    key: str, value_fn: Callable[[SystemEnergy], float | None]
) -> AlphaEssSensorEntityDescription[SystemEnergy]:
    return AlphaEssSensorEntityDescription(
        key=key,
        translation_key=key,
        native_unit_of_measurement=PERCENTAGE,
        state_class=SensorStateClass.MEASUREMENT,
        value_fn=lambda data: _percentage(value_fn(data)),
    )


ENERGY_SENSORS: tuple[AlphaEssSensorEntityDescription[SystemEnergy], ...] = (
    _energy_description("pv_energy_today", lambda data: data.daily.epv),
    _energy_description("grid_import_energy_today", lambda data: data.daily.e_input),
    _energy_description("grid_export_energy_today", lambda data: data.daily.e_output),
    _energy_description(
        "battery_charge_energy_today", lambda data: data.daily.e_charge
    ),
    _energy_description(
        "battery_discharge_energy_today", lambda data: data.daily.e_discharge
    ),
    _energy_description(
        "battery_grid_charge_energy_today", lambda data: data.daily.e_grid_charge
    ),
    _energy_description(
        "ev_energy_today", lambda data: data.daily.e_charging_pile, is_optional=True
    ),
    _energy_description("load_energy_today", lambda data: data.summary.eload),
    _energy_description("pv_energy_total", lambda data: data.summary.epvtotal),
    _rate_description("self_consumption", lambda data: data.summary.eself_consumption),
    _rate_description("self_sufficiency", lambda data: data.summary.eself_sufficiency),
)

SYSTEM_SENSORS: tuple[AlphaEssSensorEntityDescription[EssSystem], ...] = (
    AlphaEssSensorEntityDescription(
        key="battery_capacity",
        translation_key="battery_capacity",
        device_class=SensorDeviceClass.ENERGY_STORAGE,
        native_unit_of_measurement=UnitOfEnergy.KILO_WATT_HOUR,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda system: system.cobat,
    ),
    AlphaEssSensorEntityDescription(
        key="battery_usable_capacity",
        translation_key="battery_usable_capacity",
        native_unit_of_measurement=PERCENTAGE,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda system: system.us_capacity,
    ),
    AlphaEssSensorEntityDescription(
        key="inverter_nominal_power",
        translation_key="inverter_nominal_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda system: system.poinv,
    ),
    AlphaEssSensorEntityDescription(
        key="pv_nominal_power",
        translation_key="pv_nominal_power",
        device_class=SensorDeviceClass.POWER,
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda system: system.popv,
    ),
    AlphaEssSensorEntityDescription(
        key="battery_model",
        translation_key="battery_model",
        entity_category=EntityCategory.DIAGNOSTIC,
        value_fn=lambda system: system.mbat,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: AlphaEssConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """Set up the sensors of every system of the account."""
    runtime_data = entry.runtime_data
    live = runtime_data.live
    energy = runtime_data.energy
    entities: list[SensorEntity] = []
    for sys_sn, system in runtime_data.systems.items():
        entities.extend(
            AlphaEssCoordinatorSensor(live, system, description)
            for description in LIVE_SENSORS
            if description.exists_fn(live.data[sys_sn])
        )
        entities.extend(
            AlphaEssCoordinatorSensor(energy, system, description)
            for description in ENERGY_SENSORS
            if description.exists_fn(energy.data[sys_sn])
        )
        entities.extend(
            AlphaEssSystemSensor(system, description) for description in SYSTEM_SENSORS
        )
    async_add_entities(entities)


class AlphaEssCoordinatorSensor[DataT](AlphaEssCoordinatorEntity[DataT], SensorEntity):
    """Sensor whose state is updated by a coordinator."""

    entity_description: AlphaEssSensorEntityDescription[DataT]

    @property
    @override
    def native_value(self) -> StateType:
        """Return the current value of the sensor."""
        return self.entity_description.value_fn(self.system_data)


class AlphaEssSystemSensor(SensorEntity):
    """Sensor with a static value from the system list loaded at setup."""

    _attr_has_entity_name = True
    _attr_should_poll = False
    entity_description: AlphaEssSensorEntityDescription[EssSystem]

    def __init__(
        self,
        system: EssSystem,
        description: AlphaEssSensorEntityDescription[EssSystem],
    ) -> None:
        """Initialize the sensor.

        Args:
            system: System the sensor belongs to.
            description: Description of the sensor.
        """
        self.entity_description = description
        self._attr_unique_id = f"{system.sys_sn}_{description.key}"
        self._attr_device_info = system_device_info(system)
        self._attr_native_value = description.value_fn(system)
