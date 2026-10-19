"""Tests for the Alpha ESS diagnostics."""

import json

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.components.diagnostics import (
    get_diagnostics_for_config_entry,
)
from pytest_homeassistant_custom_component.typing import ClientSessionGenerator
from syrupy.assertion import SnapshotAssertion
from syrupy.filters import props


async def test_entry_diagnostics(
    hass: HomeAssistant,
    hass_client: ClientSessionGenerator,
    init_integration: MockConfigEntry,
    snapshot: SnapshotAssertion,
) -> None:
    """Test that diagnostics contain the data without credentials or serials."""
    diagnostics = await get_diagnostics_for_config_entry(
        hass, hass_client, init_integration
    )

    assert diagnostics == snapshot(
        exclude=props("created_at", "modified_at", "entry_id")
    )
    serialized = json.dumps(diagnostics)
    for secret in ("test-app-id", "test-app-secret", "AL0000000000000"):
        assert secret not in serialized
