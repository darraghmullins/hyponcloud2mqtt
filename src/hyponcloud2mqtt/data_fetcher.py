import logging
import sys
import requests
import threading
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

from .http_client import HttpClient, AuthenticationError
from .data_merger import merge_api_data

logger = logging.getLogger(__name__)


class DataFetcher:
    def __init__(self, config, system_id: str):
        self.config = config
        self.system_id = system_id
        self.base_url = config.http_url.rstrip("/")

        self.session = requests.Session()
        self.session.verify = self.config.verify_ssl

        self.monitor_client = None
        self.production_client = None
        self.status_client = None

        self._reauth_lock = threading.Lock()

        self.setup_clients()

    def _login(self) -> str | None:
        """
        Authenticate against the Hypon Cloud v2 API.
        """

        if not (
            self.config.api_username
            and self.config.api_password
        ):
            logger.warning(
                "No API credentials provided, skipping login"
            )
            return None

        login_url = f"{self.base_url}/v2/login"

        logger.info(
            "Attempting login to %s",
            login_url,
        )

        payload = {
            "username": self.config.api_username,
            "password": self.config.api_password,
            "oem": None,
        }

        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json;charset=UTF-8",
            "Origin": "https://www.hypon.cloud",
            "Referer": "https://www.hypon.cloud/",
        }

        try:
            response = self.session.post(
                login_url,
                json=payload,
                headers=headers,
                timeout=10,
            )

            logger.debug(
                "Login response status: %s",
                response.status_code,
            )

            response.raise_for_status()

            data = response.json()

            if not isinstance(data, dict):
                logger.error(
                    "Unexpected login response: %s",
                    data,
                )
                return None

            if data.get("code") != 20000:
                logger.error(
                    "Login failed: code=%s message=%s",
                    data.get("code"),
                    data.get("message"),
                )
                return None

            token = (
                data
                .get("data", {})
                .get("token")
            )

            if not token:
                logger.error(
                    "Login succeeded but no Bearer token "
                    "was returned"
                )
                return None

            logger.info(
                "Successfully logged in to Hypon Cloud"
            )

            return token

        except requests.RequestException as e:
            logger.error(
                "Error during login: %s",
                e,
            )
            return None

        except ValueError as e:
            logger.error(
                "Unable to decode login response: %s",
                e,
            )
            return None

    def setup_clients(self):
        """
        Set up clients for all Hypon Cloud v2 endpoints.
        """

        token = self._login()

        if token:
            self.session.headers.update(
                {
                    "Authorization":
                    f"Bearer {token}"
                }
            )

        elif (
            self.config.api_username
            and self.config.api_password
        ):
            logger.critical(
                "Failed to retrieve Bearer token"
            )
            sys.exit(1)

        # All plant endpoints use /v2.
        plant_base_url = (
            f"{self.base_url}/v2/plant/"
            f"{self.system_id}"
        )

        self.monitor_client = HttpClient(
            f"{plant_base_url}/monitor?refresh=true",
            self.session,
        )

        self.production_client = HttpClient(
            f"{plant_base_url}/production2",
            self.session,
        )

        self.status_client = HttpClient(
            f"{plant_base_url}/status",
            self.session,
        )

        logger.info(
            "Hypon Cloud v2 API clients initialized"
        )

    def _get_energy2_url(self) -> str:
        """
        Construct the daily energy2 API URL.

        Example:

        /v2/plant/2042196252769624064/
        energy2?day=20&month=09&type=day&year=2026
        """

        now = datetime.now()

        return (
            f"{self.base_url}/v2/plant/"
            f"{self.system_id}/energy2"
            f"?day={now.day:02d}"
            f"&month={now.month:02d}"
            f"&type=day"
            f"&year={now.year}"
        )

    def _fetch_energy2(self):
        """
        Fetch today's energy-flow data.
        """

        url = self._get_energy2_url()

        logger.debug(
            "Fetching Hypon Cloud energy data from %s",
            url,
        )

        client = HttpClient(
            url,
            self.session,
        )

        return client.fetch_data()

    def fetch_all(self):
        """
        Fetch all Hypon Cloud data concurrently.

        Endpoints:

        /v2/plant/{system_id}/monitor
        /v2/plant/{system_id}/production2
        /v2/plant/{system_id}/status
        /v2/plant/{system_id}/energy2
        """

        monitor_data = None
        production_data = None
        status_data = None
        energy_data = None

        max_retries = 2

        for attempt in range(max_retries):

            try:
                with ThreadPoolExecutor(
                    max_workers=4
                ) as executor:

                    future_monitor = executor.submit(
                        self.monitor_client.fetch_data
                    )

                    future_production = executor.submit(
                        self.production_client.fetch_data
                    )

                    future_status = executor.submit(
                        self.status_client.fetch_data
                    )

                    future_energy = executor.submit(
                        self._fetch_energy2
                    )

                    futures = [
                        future_monitor,
                        future_production,
                        future_status,
                        future_energy,
                    ]

                    for future in as_completed(futures):
                        future.result()

                    monitor_data = (
                        future_monitor.result()
                    )

                    production_data = (
                        future_production.result()
                    )

                    status_data = (
                        future_status.result()
                    )

                    energy_data = (
                        future_energy.result()
                    )

                break

            except AuthenticationError:

                logger.warning(
                    "Authentication failed "
                    "(attempt %s/%s)",
                    attempt + 1,
                    max_retries,
                )

                if attempt < max_retries - 1:

                    with self._reauth_lock:

                        logger.info(
                            "Attempting to re-authenticate"
                        )

                        new_token = self._login()

                        if new_token:

                            self.session.headers.update(
                                {
                                    "Authorization":
                                    f"Bearer {new_token}"
                                }
                            )

                            logger.info(
                                "Re-authentication successful"
                            )

                            continue

                        logger.error(
                            "Re-authentication failed"
                        )

                else:
                    logger.error(
                        "Maximum authentication retries reached"
                    )

            except Exception as e:

                logger.error(
                    "Unexpected error during data fetch: %s",
                    e,
                )

                break

        if (
            monitor_data is None
            and production_data is None
            and status_data is None
            and energy_data is None
        ):
            logger.warning(
                "No Hypon Cloud data was retrieved"
            )
            return None

        return merge_api_data(
            monitor_data,
            production_data,
            status_data,
            energy_data,
        )
