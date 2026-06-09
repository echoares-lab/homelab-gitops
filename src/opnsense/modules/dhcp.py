"""DHCP interface management for OPNsense (Kea DHCPv4 backend, OPNsense 24+)"""

from opnsense.base import BaseClient
from opnsense.exceptions import ValidationError


class DHCPClient(BaseClient):
    """Client for OPNsense Kea DHCPv4 operations"""

    def list_enabled_interfaces(self) -> list:
        """Discover all interfaces with Kea DHCP enabled.

        Returns list of dicts: [{interface, range_from, range_to, enabled}]
        """
        response = self.get('/kea/dhcpv4/get')
        general = response.get('dhcpv4', {}).get('general', {})

        if general.get('enabled') != '1':
            return []

        interfaces = general.get('interfaces', {})
        result = []
        for iface, config in interfaces.items():
            if config.get('selected') == 1:
                result.append({
                    'interface': iface,
                    'range_from': '',
                    'range_to': '',
                    'enabled': True,
                })
        return result

    def disable_interface(self, interface: str) -> dict:
        """Disable Kea DHCP on a single interface."""
        if not interface:
            raise ValidationError("Interface required")
        response = self.get('/kea/dhcpv4/get')
        general = response.get('dhcpv4', {}).get('general', {})
        interfaces = general.get('interfaces', {})
        if interface in interfaces:
            interfaces[interface]['selected'] = 0
        return self.post('/kea/dhcpv4/set', {
            'dhcpv4': {'general': {'interfaces': {interface: {'selected': '0'}}}}
        })

    def enable_interface(self, interface: str) -> dict:
        """Re-enable Kea DHCP on a single interface."""
        if not interface:
            raise ValidationError("Interface required")
        return self.post('/kea/dhcpv4/set', {
            'dhcpv4': {'general': {'interfaces': {interface: {'selected': '1'}}}}
        })
