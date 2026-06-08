"""Base client class for OPNsense module clients"""

from opnsense.client import RestClient

class BaseClient:
    """Base class for all OPNsense module clients"""

    def __init__(self, api_key: str, api_secret: str, url: str, timeout: int = 10) -> None:
        """Initialize with OPNsense API credentials"""
        self.api = RestClient(api_key, api_secret, url, timeout=timeout)

    def get(self, endpoint: str, params: dict = None) -> dict:
        """GET request to OPNsense API"""
        return self.api.get(endpoint, params)

    def post(self, endpoint: str, data: dict = None) -> dict:
        """POST request to OPNsense API"""
        return self.api.post(endpoint, data)
