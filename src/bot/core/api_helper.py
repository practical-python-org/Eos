import logging
import os

import aiohttp
import requests

logger = logging.getLogger(__name__)

# Default timeout (seconds) for all API requests so a hung API can't block the bot.
REQUEST_TIMEOUT = 10

_UNAVAILABLE = {"status": "error", "message": "API request failed"}


class API:
    """
    Thin client over the Flask API.
    """

    def __init__(self):
        logger.info("Initializing API...")
        self.api = os.getenv("FLASK_URL")
        self.headers = {"Content-Type": "application/json"}
        self.session = None

    async def setup(self):
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)

        self.session = aiohttp.ClientSession(headers=self.headers, timeout=timeout)

        logger.info("API initialized.")

    async def close(self):
        """Close the shared session. Called from the bot's shutdown hook."""
        if self.session is not None:
            await self.session.close()
            self.session = None

    ##############################
    #     Request plumbing       #
    ##############################
    def _request(self, method, path, **kwargs) -> dict:
        """Perform a blocking request and return the juice."""
        try:
            response = requests.request(
                method, f"{self.api}{path}", timeout=REQUEST_TIMEOUT, **kwargs
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

    async def _arequest(self, method, path, **kwargs) -> dict:
        """Perform a non-blocking request and return the juice."""
        try:
            async with self.session.request(
                method, f"{self.api}{path}", **kwargs
            ) as response:
                payload = await response.json(content_type=None)
        except (aiohttp.ClientError, TimeoutError, ValueError) as err:
            logger.error("API %s %s failed: %s", method, path, err)
            return dict(_UNAVAILABLE)

        if not isinstance(payload, dict):
            logger.error(
                "API %s %s returned an unexpected shape: %r", method, path, payload
            )
            return dict(_UNAVAILABLE)

        return payload

    ##############################
    #        Health checks       #
    ##############################

    async def health_check(self):
        """Returns the healthcheck status of API and DB"""
        timeout = aiohttp.ClientTimeout(total=REQUEST_TIMEOUT)
        async with aiohttp.ClientSession(timeout=timeout) as session:
            results = {}
            async with session.get(f"{self.api}/hc_api") as response:
                results["api_status"] = await response.json()
            async with session.get(f"{self.api}/hc_db") as response:
                results["db_status"] = await response.json()
            return results

    ##############################
    #           Logging          #
    ##############################
    def get_one_log_setting(self, flag_id):
        """Retrieves one log setting from the database"""
        logger.debug("Bot called get_one_log_setting endpoint.")
        return self._request("GET", f"/logging/{flag_id}")

    def get_all_log_settings(self):
        """Retrieves all log settings from the database"""
        logger.debug("Bot called the get_all_log_settings endpoint.")
        return self._request("GET", "/logging")

    def update_existing_log_setting(self, log_id, new_value):
        """Updates an existing log setting in the database"""
        logger.debug(
            f"Bot called the update_existing_log_setting endpoint. Log setting ID: {log_id} - New value: {new_value}"
        )
        return self._request("PUT", f"/logging/{log_id}", json={"value": new_value})

    ##############################
    #           Settings         #
    ##############################
    def get_one_setting(self, flag_id):
        """Retrieves one setting from the database"""
        logger.debug("Bot called get_one_setting endpoint.")
        return self._request("GET", f"/settings/{flag_id}")

    def get_all_settings(self):
        """Retrieves all settings from the database"""
        logger.debug("Bot called the get_all_settings endpoint.")
        return self._request("GET", "/settings")

    def update_existing_setting(self, setting_id, new_value):
        """Updates an existing setting in the database"""
        logger.debug(
            f"Bot called the update_existing_setting endpoint. Setting ID: {setting_id} - New value: {new_value}"
        )
        return self._request(
            "PUT", f"/settings/{setting_id}", json={"value": new_value}
        )

    ##############################
    #            Roles           #
    ##############################
    def get_one_role(self, flag_id):
        """Retrieves one role from the database"""
        logger.debug("Bot called get_one_role endpoint.")
        return self._request("GET", f"/role/{flag_id}")

    def get_all_roles(self):
        """Retrieves all roles from the database"""
        logger.debug("Bot called the get_all_roles endpoint.")
        return self._request("GET", "/role")

    def update_existing_role(self, role_id, new_value):
        """Updates an existing role in the database"""
        logger.debug(
            f"Bot called the update_existing_role endpoint. role ID: {role_id} - New value: {new_value}"
        )
        return self._request("PUT", f"/role/{role_id}", json={"value": new_value})

    ##############################
    #            Points          #
    ##############################

    async def add_user_to_points(self, user_id):
        logger.debug(f"Bot called the add_user_to_points endpoint. User ID: {user_id}")
        return await self._arequest("POST", f"/points/{user_id}/add")

    async def delete_user_from_points(self, user_id):
        logger.debug(
            f"Bot called the delete_user_from_points endpoint. User ID: {user_id}"
        )
        return await self._arequest("DELETE", f"/points/{user_id}")

    async def get_points(self, user_id):
        logger.debug(f"Bot called the get_points endpoint. User ID: {user_id}")
        return await self._arequest("GET", f"/points/{user_id}")

    def get_monthly_points(self, user_id):
        logger.debug(f"Bot called the get_monthly_points endpoint. User Id: {user_id}")
        return self._request("GET", f"/points/monthly/{user_id}")

    async def update_points(self, user_id, amount):
        logger.debug(
            f"Bot called the update_points endpoint. User ID: {user_id} - Points: {amount}"
        )
        return await self._arequest(
            "POST", f"/points/{user_id}/update", json={"value": amount}
        )

    async def top_10(self):
        logger.debug("Bot called the top_10 endpoint.")
        return await self._arequest("GET", "/points/top10")

    def monthly_top_point_earner(self):
        logger.debug("Bot called monthly top point earner.")
        return self._request("GET", "/points/monthly/top")

    def monthly_top_10(self):
        logger.debug("Bot called the monthly top_10 endpoint.")
        return self._request("GET", "/points/monthly/top10")

    def reset_monthly_points(self):
        logger.debug("Bot called the reset monthly points endpoint.")
        return self._request("DELETE", "/points/monthly/reset")

    ##############################
    #        Parameters          #
    ##############################

    def get_parameter(self, parameter_name):
        logger.debug(
            f"Bot called parameters endpoint to get parameter {parameter_name}"
        )
        return self._request("GET", f"/parameters/{parameter_name}")

    def set_parameter(self, parameter_name, parameter_value):
        logger.debug(
            f"Bot called parameters endpoint to set {parameter_name} to {parameter_value}"
        )
        return self._request(
            "PUT", f"/parameters/{parameter_name}", json={"value": parameter_value}
        )
