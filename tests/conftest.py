"""Fixtures for the Alpha ESS integration tests."""

from collections.abc import Generator
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

from alphaessaio.models import DailyEnergy, EssSystem, LastPowerData, SystemSummary
from homeassistant.core import HomeAssistant
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.syrupy import HomeAssistantSnapshotExtension
from syrupy.assertion import SnapshotAssertion

from custom_components.alpha_ess.const import CONF_APP_ID, CONF_APP_SECRET, DOMAIN

_FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_payload(name: str) -> Any:
    """Return the "data" part of a recorded AlphaESS response."""
    return json.loads((_FIXTURES_DIR / f"{name}.json").read_text())["data"]


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Allow Home Assistant to load the integration from custom_components."""


@pytest.fixture
def snapshot(snapshot: SnapshotAssertion) -> SnapshotAssertion:
    """Store snapshots in tests/snapshots with the Home Assistant serializer.

    pytest-homeassistant-custom-component defines the same override, but whether
    it or syrupy's plain fixture wins depends on the plugin load order, which
    differs between machines.
    """
    return snapshot.use_extension(HomeAssistantSnapshotExtension)


@pytest.fixture
def entity_registry_enabled_by_default() -> Generator[None]:
    """Enable entities that are disabled by default."""
    with patch(
        "homeassistant.helpers.entity.Entity.entity_registry_enabled_default",
        return_value=True,
    ):
        yield


@pytest.fixture
def ess_list_fixture() -> str:
    """Return the fixture used for the system list."""
    return "getEssList"


@pytest.fixture
def live_fixture() -> str:
    """Return the fixture used for live power data."""
    return "getLastPowerData"


@pytest.fixture
def mock_config_entry() -> MockConfigEntry:
    """Return a config entry for an account with one system."""
    return MockConfigEntry(
        domain=DOMAIN,
        title="Alpha ESS AL0000000000000",
        data={CONF_APP_ID: "test-app-id", CONF_APP_SECRET: "test-app-secret"},
        unique_id="test-app-id",
    )


@pytest.fixture
def mock_setup_entry() -> Generator[AsyncMock]:
    """Skip the setup of the config entry created by a config flow."""
    with patch(
        "custom_components.alpha_ess.async_setup_entry", return_value=True
    ) as setup_entry_mock:
        yield setup_entry_mock


@pytest.fixture
def mock_alphaess_client(
    ess_list_fixture: str, live_fixture: str
) -> Generator[MagicMock]:
    """Return a mocked AlphaESS client that answers with recorded responses."""
    with (
        patch("custom_components.alpha_ess.AlphaEssAPI", autospec=True) as api_mock,
        patch("custom_components.alpha_ess.config_flow.AlphaEssAPI", new=api_mock),
    ):
        client = api_mock.return_value
        client.get_ess_list.return_value = [
            EssSystem.model_validate(system)
            for system in _load_payload(ess_list_fixture)
        ]
        client.get_last_power_data.return_value = LastPowerData.model_validate(
            _load_payload(live_fixture)
        )
        client.get_one_date_energy_by_sn.return_value = DailyEnergy.model_validate(
            _load_payload("getOneDateEnergyBySn")
        )
        client.get_sum_data_for_customer.return_value = SystemSummary.model_validate(
            _load_payload("getSumDataForCustomer")
        )
        yield client


@pytest.fixture
async def init_integration(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_alphaess_client: MagicMock,
) -> MockConfigEntry:
    """Set up the integration with the mocked client."""
    mock_config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(mock_config_entry.entry_id)
    await hass.async_block_till_done()

    return mock_config_entry
