"""Tests for the Alpha ESS config flow."""

from unittest.mock import AsyncMock, MagicMock

from alphaessaio import AlphaEssAuthError, AlphaEssConnectionError, AlphaEssRequestError
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.alpha_ess.const import CONF_APP_ID, CONF_APP_SECRET, DOMAIN

pytestmark = pytest.mark.usefixtures("mock_setup_entry")

_USER_INPUT = {CONF_APP_ID: "test-app-id", CONF_APP_SECRET: "test-app-secret"}

_ERROR_CASES = pytest.mark.parametrize(
    ("side_effect", "expected_error"),
    [
        (AlphaEssAuthError("rejected", code=6007), "invalid_auth"),
        (AlphaEssConnectionError, "cannot_connect"),
        (AlphaEssRequestError("rejected", code=6001), "cannot_connect"),
        (RuntimeError, "unknown"),
    ],
    ids=["invalid_auth", "connection_error", "request_error", "unexpected_error"],
)


@pytest.mark.usefixtures("mock_alphaess_client")
async def test_user_flow_creates_entry(
    hass: HomeAssistant, mock_setup_entry: AsyncMock
) -> None:
    """Test that valid credentials create an entry named after the system."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={**_USER_INPUT, CONF_APP_ID: " test-app-id "}
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Alpha ESS AL0000000000000"
    assert result["data"] == _USER_INPUT
    assert result["result"].unique_id == "test-app-id"
    assert len(mock_setup_entry.mock_calls) == 1


@pytest.mark.parametrize("ess_list_fixture", ["getEssList_two_systems"])
@pytest.mark.usefixtures("mock_alphaess_client")
async def test_user_flow_title_with_two_systems(hass: HomeAssistant) -> None:
    """Test that an account with several systems gets a generic title."""
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Alpha ESS"


@_ERROR_CASES
async def test_user_flow_errors(
    hass: HomeAssistant,
    mock_alphaess_client: MagicMock,
    side_effect: Exception | type[Exception],
    expected_error: str,
) -> None:
    """Test that validation errors are shown and the user can retry."""
    mock_alphaess_client.get_ess_list.side_effect = side_effect
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    mock_alphaess_client.get_ess_list.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )

    assert result["type"] is FlowResultType.CREATE_ENTRY


@pytest.mark.usefixtures("mock_alphaess_client")
async def test_user_flow_already_configured(
    hass: HomeAssistant, mock_config_entry: MockConfigEntry
) -> None:
    """Test that an AppID can only be configured once."""
    mock_config_entry.add_to_hass(hass)
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_user_flow_no_systems(
    hass: HomeAssistant, mock_alphaess_client: MagicMock
) -> None:
    """Test that an account without systems is rejected."""
    mock_alphaess_client.get_ess_list.return_value = []
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input=_USER_INPUT
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "no_systems"
    assert result["description_placeholders"] == {
        "developer_portal_url": "https://open.alphaess.com/"
    }


async def test_reauth_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_alphaess_client: MagicMock,
) -> None:
    """Test that reauthentication stores the new secret and keeps the AppID."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_APP_SECRET: "new-app-secret"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert mock_config_entry.data == {
        CONF_APP_ID: "test-app-id",
        CONF_APP_SECRET: "new-app-secret",
    }


@_ERROR_CASES
async def test_reauth_flow_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_alphaess_client: MagicMock,
    side_effect: Exception | type[Exception],
    expected_error: str,
) -> None:
    """Test that reauthentication errors are shown and the user can retry."""
    mock_config_entry.add_to_hass(hass)
    mock_alphaess_client.get_ess_list.side_effect = side_effect
    result = await mock_config_entry.start_reauth_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_APP_SECRET: "new-app-secret"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    mock_alphaess_client.get_ess_list.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_APP_SECRET: "new-app-secret"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"


async def test_reconfigure_flow(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_alphaess_client: MagicMock,
) -> None:
    """Test that reconfiguration stores the new secret."""
    mock_config_entry.add_to_hass(hass)
    result = await mock_config_entry.start_reconfigure_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reconfigure"

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_APP_SECRET: "new-app-secret"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
    assert mock_config_entry.data[CONF_APP_SECRET] == "new-app-secret"


@_ERROR_CASES
async def test_reconfigure_flow_errors(
    hass: HomeAssistant,
    mock_config_entry: MockConfigEntry,
    mock_alphaess_client: MagicMock,
    side_effect: Exception | type[Exception],
    expected_error: str,
) -> None:
    """Test that reconfiguration errors are shown and the user can retry."""
    mock_config_entry.add_to_hass(hass)
    mock_alphaess_client.get_ess_list.side_effect = side_effect
    result = await mock_config_entry.start_reconfigure_flow(hass)

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_APP_SECRET: "new-app-secret"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": expected_error}

    mock_alphaess_client.get_ess_list.side_effect = None
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], user_input={CONF_APP_SECRET: "new-app-secret"}
    )

    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reconfigure_successful"
