"""Low-level REST client for OPNsense API"""

import json
import requests
from opnsense.exceptions import (
    BadRequest,
    Unauthorized,
    ServerError,
    TimeoutError as OPNTimeoutError,
    OPNsenseError,
)

class RestClient:
    """Wrapper around requests for OPNsense API calls"""

    def __init__(self, api_key: str, api_secret: str, url: str, timeout: int = 10):
        if not api_key:
            raise ValueError("api_key is required")
        if not api_secret:
            raise ValueError("api_secret is required")
        if not url:
            raise ValueError("url is required")

        self.api_key = api_key
        self.api_secret = api_secret
        self.url = url.rstrip('/')
        self.timeout = timeout
        self.auth = (api_key, api_secret)

    def get(self, endpoint: str, params: dict = None) -> dict:
        """GET request to OPNsense API"""
        full_url = f"{self.url}{endpoint}"

        try:
            response = requests.get(
                full_url,
                auth=self.auth,
                params=params,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise OPNTimeoutError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise OPNsenseError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise OPNsenseError(f"Request failed: {e}")

        return self._handle_response(response)

    def post(self, endpoint: str, data: dict = None) -> dict:
        """POST request to OPNsense API"""
        full_url = f"{self.url}{endpoint}"

        try:
            response = requests.post(
                full_url,
                auth=self.auth,
                json=data,
                timeout=self.timeout
            )
        except requests.exceptions.Timeout:
            raise OPNTimeoutError(f"Request timed out after {self.timeout}s")
        except requests.exceptions.ConnectionError as e:
            raise OPNsenseError(f"Connection error: {e}")
        except requests.exceptions.RequestException as e:
            raise OPNsenseError(f"Request failed: {e}")

        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> dict:
        """Handle HTTP response, raise exceptions for errors"""
        if response.status_code == 401:
            raise Unauthorized(f"401 Unauthorized: Invalid API credentials")
        elif response.status_code >= 500:
            raise ServerError(f"{response.status_code} Server Error: {response.text}")
        elif response.status_code >= 400:
            raise BadRequest(f"{response.status_code} Error: {response.text}")

        try:
            return response.json()
        except (json.JSONDecodeError, ValueError) as e:
            raise BadRequest(f"Invalid JSON response: {e}")
