"""Network management (VLANs, interfaces) for OPNsense"""

from opnsense.base import BaseClient
from opnsense.exceptions import ValidationError

class NetworkClient(BaseClient):
    """Client for OPNsense network operations"""

    def create_vlan(self, interface: str, vlan_id: int, description: str, **kwargs) -> dict:
        """Create a VLAN"""

        # Validation
        if not interface:
            raise ValidationError("Interface required")
        if vlan_id < 1 or vlan_id > 4094:
            raise ValidationError(f"Invalid VLAN ID: {vlan_id}. Must be 1-4094")
        if not description:
            raise ValidationError("Description required")

        # Build payload
        payload = {
            'interface': interface,
            'vlan_id': vlan_id,
            'description': description,
        }
        payload.update(kwargs)

        return self.post('/network/vlans/set', payload)

    def list_vlans(self) -> list:
        """List all VLANs"""
        response = self.get('/network/vlans/get')
        return response.get('rows', [])

    def get_vlan(self, vlan_id: str) -> dict:
        """Get a specific VLAN by ID"""
        response = self.get(f'/network/vlans/get/{vlan_id}')
        return response.get('vlan', {})

    def delete_vlan(self, vlan_id: str) -> dict:
        """Delete a VLAN by ID"""
        return self.post(f'/network/vlans/delete/{vlan_id}', {})

    def list_interfaces(self) -> list:
        """List all network interfaces"""
        response = self.get('/network/interfaces/get')
        return response.get('interfaces', [])

    def get_interface(self, name: str) -> dict:
        """Get a specific interface by name"""
        response = self.get(f'/network/interfaces/get/{name}')
        return response.get('interface', {})

    def configure_interface(self, name: str, **kwargs) -> dict:
        """Configure an interface with full field support"""
        payload = kwargs
        return self.post(f'/network/interfaces/set/{name}', payload)
