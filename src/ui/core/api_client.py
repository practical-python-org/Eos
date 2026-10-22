import logging
import os

import requests

logger = logging.getLogger(__name__)

# Default timeout (seconds) for all API requests so a hung API can't block the UI.
REQUEST_TIMEOUT = 10

_UNAVAILABLE = {"status": "error", "message": "API request failed"}


class API:
    """
    Thin blocking client over the Flask API.

    Mirrors the bot's ``core/api_helper.py`` contract: every call returns the
    standard envelope, and transport failures are logged and folded into an
    ``error`` envelope rather than raised.
    """

    def __init__(self):
        logger.info("Initializing API client...")
        self.api = os.getenv("FLASK_URL")
        self.headers = {"Content-Type": "application/json"}

    def _request(self, method, path, **kwargs) -> dict:
        """Perform a blocking request and return the juice."""
        try:
            response = requests.request(
                method,
                f"{self.api}{path}",
                headers=self.headers,
                timeout=REQUEST_TIMEOUT,
                **kwargs,
            )
            payload = response.json()
        except requests.RequestException as err:
            logger.error("API %s %s failed: %s", method, path, err)
            return dict(_UNAVAILABLE)
        except ValueError:
            logger.error("API %s %s returned a non-JSON body", method, path)
            return dict(_UNAVAILABLE)

        if not isinstance(payload, dict):
            logger.error(
                "API %s %s returned an unexpected shape: %r", method, path, payload
            )
            return dict(_UNAVAILABLE)

        return payload

    def health_check(self) -> dict:
        """Returns the healthcheck status of the API."""
        return self._request("GET", "/hc_api")

    def get_settings(self) -> dict:
        """Returns every row of ``serversettings``."""
        return self._request("GET", "/settings")

    def update_setting(self, setting_id, value) -> dict:
        """Writes a new value onto a single ``serversettings`` row."""
        return self._request("PUT", f"/settings/{setting_id}", json={"value": value})
