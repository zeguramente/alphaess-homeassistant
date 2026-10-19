"""Tests for the setup of the Alpha ESS integration."""

from unittest.mock import MagicMock

from alphaessaio import AlphaEssAuthError, AlphaEssConnectionError
from freezegun.api import FrozenDateTimeFactory
from homeassistant.config_entries import SOURCE_REAUTH, ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers import device_registry as dr, entity_registry as er
import pytest
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_fire_time_changed,
)

from custom_components.alpha_ess.const import DOMAIN, LIVE_UPDATE_INTERVAL

_SYS_SN = "AL0000000000000"


async def _refresh_live_data(
    hass: HomeAssistant, freezer: FrozenDateTimeFactory
) -> None:
    freezer.tick(LIVE_UPDATE_INTERVAL)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


async def test_load_unload_entry(
    hass: HomeAssistant, init_integration: MockConfigEntry
) -> None:
    """Test that the entry loads and unloads."""
    assert init_integration.state is ConfigEntryState.LOADED

    await hass.config_entries.async_unload(init_integration.entry_id)
    await hass.async_block_till_done()

    assert init_integration.state is ConfigEntryState.NOT_LOADED


@pytest.mark.parametrize(
    ("ess_list_side_effect", "ess_list_return_value", "expected_state"),
    [
        (AlphaEssConnectionError, None, ConfigEntryState.SETUP_RETRY),
        (AlphaEssAuthError("rejected", code=6007), None, ConfigEntryState.SETUP_ERROR),
        (None, [], ConfigEntryState.SETUP_ERROR),
    ],
    ids=["cloud_unreachable", "invalid_auth", "no_systems"],
)
async def test_setup_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_alphaess_client: MagicMock,
    ess_list_side_effect: Exception | type[Exception] | None,
    ess_list_return_value: list[object] | None,
    expected_state: ConfigEntryState,
) -> None:
    """Test the entry state when the system list cannot be loaded."""
    mock_alphaess_client.get_ess_list.side_effect = ess_list_side_effect
    if ess_list_return_value is not None:
        mock_alphaess_client.get_ess_list.return_value = ess_list_return_value
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    assert mock_config_entry.state is expected_state


@pytest.mark.parametrize("ess_list_fixture", ["getEssList_two_systems"])
async def test_device_per_system(
    device_registry: dr.DeviceRegistry, init_integration: MockConfigEntry
) -> None:
    """Test that every system of the account gets its own device."""
    devices = dr.async_entries_for_config_entry(
        device_registry, init_integration.entry_id
    )

    assert {
        (device.serial_number, device.model, device.manufacturer) for device in devices
    } == {
        ("AL0000000000000", "SMILE-S6-HV-INV", "Alpha ESS"),
        ("AL0000000000001", "SMILE-G3-S5", "Alpha ESS"),
    }
    assert {next(iter(device.identifiers)) for device in devices} == {
        (DOMAIN, "AL0000000000000"),
        (DOMAIN, "AL0000000000001"),
    }


@pytest.mark.usefixtures("init_integration")
async def test_auth_error_during_polling_starts_reauth(
    hass: HomeAssistant,
    mock_alphaess_client: MagicMock,
    freezer: FrozenDateTimeFactory,
) -> None:
    """Test that rejected credentials during polling start a reauth flow."""
    mock_alphaess_client.get_last_power_data.side_effect = AlphaEssAuthError(
        "rejected", code=6007
    )

    await _refresh_live_data(hass, freezer)

    flows = hass.config_entries.flow.async_progress()
    assert len(flows) == 1
    assert flows[0]["context"]["source"] == SOURCE_REAUTH


@pytest.mark.usefixtures("init_integration")
async def test_entities_unavailable_and_recover(
    hass: HomeAssistant,
    entity_registry: er.EntityRegistry,
    mock_alphaess_client: MagicMock,
    freezer: FrozenDateTimeFactory,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Test that entities become unavailable on errors and recover afterwards."""
    pv_power_entity_id = entity_registry.async_get_entity_id(
        Platform.SENSOR, DOMAIN, f"{_SYS_SN}_pv_power"
    )
    assert pv_power_entity_id is not None
    live_data = mock_alphaess_client.get_last_power_data.return_value

    mock_alphaess_client.get_last_power_data.side_effect = AlphaEssConnectionError
    await _refresh_live_data(hass, freezer)
    await _refresh_live_data(hass, freezer)

    state = hass.states.get(pv_power_entity_id)
    assert state is not None
    assert state.state == STATE_UNAVAILABLE

    mock_alphaess_client.get_last_power_data.side_effect = None
    mock_alphaess_client.get_last_power_data.return_value = live_data
    await _refresh_live_data(hass, freezer)

    state = hass.states.get(pv_power_entity_id)
    assert state is not None
    assert state.state == "0.0"
    assert caplog.text.count("Error fetching alpha_ess_live data") == 1
    assert caplog.text.count("Fetching alpha_ess_live data recovered") == 1


async def test_stale_device_removed(
    hass: HomeAssistant,
    device_registry: dr.DeviceRegistry,
    mock_config_entry: MockConfigEntry,
    mock_alphaess_client: MagicMock,
) -> None:
    """Test that devices of systems no longer in the account are removed."""
    mock_config_entry.add_to_hass(hass)
    device_registry.async_get_or_create(
        config_entry_id=mock_config_entry.entry_id,
        identifiers={(DOMAIN, "AL9999999999999")},
    )

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    entry_id = mock_config_entry.entry_id
    assert (
        device_registry.async_get_device_by_identifier(
            (DOMAIN, "AL9999999999999"), entry_id
        )
        is None
    )
    assert (
        device_registry.async_get_device_by_identifier((DOMAIN, _SYS_SN), entry_id)
        is not None
    )
