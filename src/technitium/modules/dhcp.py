"""DHCP scope management for Technitium DNS Server"""

from technitium.base import TechnitiumBaseClient
from technitium.exceptions import TechnitiumValidationError


class TechnitiumDHCPClient(TechnitiumBaseClient):
    """Client for Technitium DHCP scope operations"""

    def list_scopes(self) -> list:
        """List all DHCP scopes.

        Returns list of dicts: [{name, enabled, networkAddress, ...}]
        """
        response = self.get('/api/dhcp/scopes/list')
        return response.get('response', {}).get('scopes', [])

    def enable_scope(self, name: str) -> dict:
        """Enable a DHCP scope by name."""
        if not name:
            raise TechnitiumValidationError("Scope name required")
        return self.get('/api/dhcp/scopes/enable', {'name': name})

    def disable_scope(self, name: str) -> dict:
        """Disable a DHCP scope by name."""
        if not name:
            raise TechnitiumValidationError("Scope name required")
        return self.get('/api/dhcp/scopes/disable', {'name': name})
