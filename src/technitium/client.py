"""Low-level REST client for Technitium DNS Server API"""

import requests
from technitium.exceptions import (
    TechnitiumError,
    TechnitiumBadRequest,
    TechnitiumUnauthorized,
    TechnitiumServerError,
    TechnitiumTimeoutError,
)


class TechnitiumRestClient:
    """Wrapper around requests for Technitium API calls (token auth)"""

    def __init__(self, host: str, token: str, timeout: int = 10) -> None:
        if not host:
            raise ValueError("host is required")
        if not token:
            raise ValueError("token is required")
        self.host = host.rstrip('/')
        self.token = token
        self.timeout = timeout

    def get(self, endpoint: str, params: dict = None) -> dict:
        """GET request to Technitium API with token auth"""
        full_url = f"{self.host}{endpoint}"
        all_params = {'token': self.token}
        if params:
            all_params.update(params)

        try:
            response = requests.get(full_url, params=all_params, timeout=self.timeout)
        except requests.exceptions.Timeout:
            raise TechnitiumTimeoutError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise TechnitiumError(f"Connection error: {e}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> dict:
        if response.status_code == 401:
            raise TechnitiumUnauthorized("401 Unauthorized: Invalid API token")
        elif response.status_code >= 500:
            raise TechnitiumServerError(f"{response.status_code} Server Error: {response.text}")
        elif response.status_code >= 400:
            raise TechnitiumBadRequest(f"{response.status_code} Error: {response.text}")

        data = response.json()
        if data.get('status') == 'error':
            raise TechnitiumError(data.get('errorMessage', 'Unknown Technitium error'))

        return data
