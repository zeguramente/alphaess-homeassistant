"""Constants for the Alpha ESS integration."""

from datetime import timedelta
import logging
from typing import Final

DOMAIN: Final = "alpha_ess"
LOGGER = logging.getLogger(__package__)

MANUFACTURER: Final = "Alpha ESS"
DEVELOPER_PORTAL_URL: Final = "https://open.alphaess.com/"

CONF_APP_ID: Final = "app_id"
CONF_APP_SECRET: Final = "app_secret"

LIVE_UPDATE_INTERVAL: Final = timedelta(seconds=60)
ENERGY_UPDATE_INTERVAL: Final = timedelta(minutes=5)
