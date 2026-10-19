"""Tests for the Alpha ESS sensors."""

from datetime import date, timedelta
from unittest.mock import MagicMock

from alphaessaio import AlphaEssConnectionError
from freezegun.api import FrozenDateTimeFactory
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
    snapshot_platform,
)
from syrupy.assertion import SnapshotAssertion

from custom_components.alpha_ess.const import (
    DOMAIN,
    ENERGY_UPDATE_INTERVAL,
    LIVE_UPDATE_INTERVAL,
)

_SYS_SN = "AL0000000000000"


def _entity_id(entity_registry: er.EntityRegistry, key: str) -> str:
    entity_id = entity_registry.async_get_entity_id(
        Platform.SENSOR, DOMAIN, f"{_SYS_SN}_{key}"
    )
    assert entity_id is not None, f"no sensor with key {key}"
    return entity_id


def _state(hass: HomeAssistant, entity_registry: er.EntityRegistry, key: str) -> str:
    state = hass.states.get(_entity_id(entity_registry, key))
    assert state is not None
    return state.state


async def _refresh(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory, interval: timedelta
) -> None:
    freezer.tick(interval)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


@pytest.mark.usefixtures("entity_registry_enabled_by_default")
async def test_all_sensors(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test all sensors against the snapshot."""
    await snapshot_platform(hass, entity_registry, snapshot, init_integration.entry_id)


@pytest.mark.usefixtures("init_integration")
async def test_grid_import_export_power(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_alphaess_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that grid power is split into import and export power."""
    assert _state(hass, entity_registry, "grid_import_power") == "3230.0"
    assert _state(hass, entity_registry, "grid_export_power") == "0.0"

    live_data = mock_alphaess_client.get_last_power_data.return_value
    mock_alphaess_client.get_last_power_data.return_value = live_data.model_copy(
        update={"pgrid": -500.0}
    )
    await _refresh(hass, freezer, LIVE_UPDATE_INTERVAL)

    assert _state(hass, entity_registry, "grid_import_power") == "0.0"
    assert _state(hass, entity_registry, "grid_export_power") == "500.0"


@pytest.mark.parametrize("live_fixture", ["getLastPowerData_minimal"])
@pytest.mark.usefixtures("init_integration")
async def test_optional_sensors_not_created(
    entity_registry: er.EntityRegistry,
) -> None:
    """Test that sensors for values the system does not report are not created."""
    optional_keys = [
        "ev_power",
        *(f"pv_string_{string}_power" for string in range(1, 5)),
        "pv_dc_meter_power",
        *(f"grid_power_l{phase}" for phase in range(1, 4)),
        *(f"inverter_power_l{phase}" for phase in range(1, 4)),
    ]

    created_keys = [
        key
        for key in optional_keys
        if entity_registry.async_get_entity_id(
            Platform.SENSOR, DOMAIN, f"{_SYS_SN}_{key}"
        )
    ]

    assert created_keys == []


@pytest.mark.usefixtures("init_integration")
async def test_missing_value_is_unknown(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_alphaess_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that a value missing in the response is unknown instead of 0."""
    live_data = mock_alphaess_client.get_last_power_data.return_value
    mock_alphaess_client.get_last_power_data.return_value = live_data.model_copy(
        update={"soc": None}
    )

    await _refresh(hass, freezer, LIVE_UPDATE_INTERVAL)

    assert _state(hass, entity_registry, "battery_state_of_charge") == STATE_UNKNOWN


@pytest.mark.parametrize(
    "key",
    [
        *(f"pv_string_{string}_power" for string in range(1, 5)),
        "pv_dc_meter_power",
        *(f"grid_power_l{phase}" for phase in range(1, 4)),
        *(f"inverter_power_l{phase}" for phase in range(1, 4)),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_detail_sensors_disabled_by_default(
    entity_registry: er.EntityRegistry, key: str
) -> None:
    """Test that per-string and per-phase sensors are disabled by default."""
    entity_entry = entity_registry.async_get(_entity_id(entity_registry, key))

    assert entity_entry is not None
    assert entity_entry.disabled_by is er.RegistryEntryDisabler.INTEGRATION


@pytest.mark.parametrize(
    ("key", "expected_state", "expected_unit", "expected_state_class"),
    [
        ("pv_energy_today", "9.3", "kWh", "total_increasing"),
        ("grid_import_energy_today", "11.94", "kWh", "total_increasing"),
        ("grid_export_energy_today", "0.02", "kWh", "total_increasing"),
        ("battery_charge_energy_today", "5.31", "kWh", "total_increasing"),
        ("battery_discharge_energy_today", "5.15", "kWh", "total_increasing"),
        ("battery_grid_charge_energy_today", "0.33", "kWh", "total_increasing"),
        ("load_energy_today", "15.4", "kWh", "total_increasing"),
        ("pv_energy_total", "16521.0", "kWh", "total_increasing"),
        ("self_consumption", "61.0", "%", "measurement"),
        ("self_sufficiency", "67.0", "%", "measurement"),
    ],
)
@pytest.mark.usefixtures("init_integration")
async def test_energy_sensor_values(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    key: str,
    expected_state: str,
    expected_unit: str,
    expected_state_class: str,
) -> None:
    """Test the energy sensors, including the rates shown as 0-100 %."""
    state = hass.states.get(_entity_id(entity_registry, key))

    assert state is not None
    assert state.state == expected_state
    assert state.attributes["unit_of_measurement"] == expected_unit
    assert state.attributes["state_class"] == expected_state_class


@pytest.mark.freeze_time("2026-10-18 23:58:00+02:00")
async def test_energy_query_date_follows_local_midnight(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_alphaess_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that the daily energy is queried for the new day after midnight."""
    await hass.config.async_set_time_zone("Europe/Berlin")
    mock_config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()
    energy_call = mock_alphaess_client.get_one_date_energy_by_sn.call_args
    assert energy_call.args == (_SYS_SN, date(2026, 10, 18))

    freezer.move_to("2026-10-19 00:03:00+02:00")
    async_fire_time_changed(hass)
    await hass.async_block_till_done()

    energy_call = mock_alphaess_client.get_one_date_energy_by_sn.call_args
    assert energy_call.args == (_SYS_SN, date(2026, 10, 19))


@pytest.mark.usefixtures("init_integration")
async def test_energy_failure_keeps_live_sensors(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_alphaess_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that a failing energy update does not affect the live sensors."""
    mock_alphaess_client.get_one_date_energy_by_sn.side_effect = AlphaEssConnectionError

    await _refresh(hass, freezer, ENERGY_UPDATE_INTERVAL)

    assert _state(hass, entity_registry, "pv_energy_today") == STATE_UNAVAILABLE
    assert _state(hass, entity_registry, "pv_power") != STATE_UNAVAILABLE
