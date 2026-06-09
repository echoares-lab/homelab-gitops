"""DHCP interface management for OPNsense (dnsmasq backend)"""

from opnsense.base import BaseClient
from opnsense.exceptions import ValidationError


class DHCPClient(BaseClient):
    """Client for OPNsense dnsmasq DHCP operations.

    dnsmasq serves both DNS and DHCP in OPNsense. Disabling DHCP per-interface
    uses the `no_interface` exclusion list rather than deleting range entries,
    so DNS continues to work unaffected.
    """

    # Map interface name → human-readable label from dnsmasq config
    _IFACE_MAP = {
        'opt1': 'MGMT_VLAN_10',
        'opt2': 'SERVERS_VLAN_20',
        'opt3': 'CLIENTS_VLAN_30',
        'opt4': 'IOT_VLAN_40',
        'opt5': 'WORK_VLAN_50',
        'opt6': 'LAB_VLAN_60',
        'opt7': 'ADMIN_VLAN_70',
        'opt8': 'GUEST_VLAN_100',
        'lan': 'LAN',
    }

    def _get_no_interface_set(self) -> set:
        """Return the set of interfaces currently excluded from DHCP."""
        response = self.get('/dnsmasq/settings/get')
        no_iface = response.get('dnsmasq', {}).get('dhcp', {}).get('no_interface', {})
        return {iface for iface, cfg in no_iface.items() if cfg.get('selected') == 1}

    def _get_dhcp_ranges(self) -> dict:
        """Return {interface: range_config} for interfaces with active DHCP ranges."""
        response = self.get('/dnsmasq/settings/get')
        ranges = response.get('dnsmasq', {}).get('dhcp_ranges', {})
        result = {}
        for uuid, cfg in ranges.items():
            iface_map = cfg.get('interface', {})
            for iface, iface_cfg in iface_map.items():
                if iface_cfg.get('selected') == 1:
                    result[iface] = {
                        'range_from': cfg.get('start_addr', ''),
                        'range_to': cfg.get('end_addr', ''),
                        'uuid': uuid,
                    }
        return result

    def list_enabled_interfaces(self) -> list:
        """Discover all interfaces actively serving DHCP via dnsmasq.

        Returns list of dicts: [{interface, range_from, range_to, enabled}]
        """
        excluded = self._get_no_interface_set()
        ranges = self._get_dhcp_ranges()
        result = []
        for iface, cfg in ranges.items():
            if iface not in excluded:
                result.append({
                    'interface': iface,
                    'range_from': cfg['range_from'],
                    'range_to': cfg['range_to'],
                    'enabled': True,
                })
        return result

    def disable_interface(self, interface: str) -> dict:
        """Disable DHCP on a single dnsmasq interface (DNS keeps running)."""
        if not interface:
            raise ValidationError("Interface required")
        current_excluded = self._get_no_interface_set()
        current_excluded.add(interface)
        result = self.post('/dnsmasq/settings/set', {
            'dnsmasq': {'dhcp': {'no_interface': ','.join(sorted(current_excluded))}}
        })
        self.post('/dnsmasq/service/reconfigure', {})
        return result

    def enable_interface(self, interface: str) -> dict:
        """Re-enable DHCP on a dnsmasq interface (rollback)."""
        if not interface:
            raise ValidationError("Interface required")
        current_excluded = self._get_no_interface_set()
        current_excluded.discard(interface)
        result = self.post('/dnsmasq/settings/set', {
            'dnsmasq': {'dhcp': {'no_interface': ','.join(sorted(current_excluded))}}
        })
        self.post('/dnsmasq/service/reconfigure', {})
        return result
