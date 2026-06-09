"""DHCP interface management for OPNsense"""

from opnsense.base import BaseClient
from opnsense.exceptions import ValidationError


class DHCPClient(BaseClient):
    """Client for OPNsense DHCPv4 operations"""

    def list_enabled_interfaces(self) -> list:
        """Discover all interfaces with DHCP currently enabled.

        Returns list of dicts: [{interface, range_from, range_to, enabled}]
        """
        response = self.get('/api/dhcpv4/settings/get')
        dhcpd = response.get('dhcpd', {})

        result = []
        for interface, config in dhcpd.items():
            if config.get('enable') == '1':
                result.append({
                    'interface': interface,
                    'range_from': config.get('range', {}).get('from', ''),
                    'range_to': config.get('range', {}).get('to', ''),
                    'enabled': True,
                })
        return result

    def disable_interface(self, interface: str) -> dict:
        """Disable DHCP on a single interface."""
        if not interface:
            raise ValidationError("Interface required")
        return self.post('/api/dhcpv4/settings/set', {
            'dhcpd': {interface: {'enable': '0'}}
        })

    def enable_interface(self, interface: str) -> dict:
        """Re-enable DHCP on a single interface."""
        if not interface:
            raise ValidationError("Interface required")
        return self.post('/api/dhcpv4/settings/set', {
            'dhcpd': {interface: {'enable': '1'}}
        })
