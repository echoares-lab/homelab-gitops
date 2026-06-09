"""Base client class for Technitium module clients"""

from technitium.client import TechnitiumRestClient


class TechnitiumBaseClient:
    """Base class for all Technitium module clients"""

    def __init__(self, host: str, token: str, timeout: int = 10) -> None:
        self.api = TechnitiumRestClient(host, token, timeout=timeout)

    def get(self, endpoint: str, params: dict = None) -> dict:
        return self.api.get(endpoint, params)
