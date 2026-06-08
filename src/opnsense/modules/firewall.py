"""Firewall rule management for OPNsense"""

import re
from opnsense.base import BaseClient
from opnsense.exceptions import ValidationError

class FirewallClient(BaseClient):
    """Client for OPNsense firewall rule operations"""

    VALID_PROTOCOLS = ['tcp', 'udp', 'icmp', 'esp', 'ah', 'gre', 'ip']
    VALID_ACTIONS = ['pass', 'block', 'reject']
    VALID_DIRECTIONS = ['in', 'out']
    VALID_STATE_POLICIES = ['established', 'new', 'closed', 'none']

    def create_firewall_rule(self, name: str, src_net: str, dst_net: str,
                            protocol: str, port: int = None, action: str = None,
                            **kwargs) -> dict:
        """Create a firewall rule with full field support"""

        # Validation
        self._validate_rule_name(name)
        self._validate_cidr(src_net, 'src_net')
        self._validate_cidr(dst_net, 'dst_net')
        self._validate_protocol(protocol)
        self._validate_action(action)

        if protocol in ['tcp', 'udp'] and port is not None:
            self._validate_port(port)

        # Build payload
        payload = {
            'name': name,
            'src_net': src_net,
            'dst_net': dst_net,
            'protocol': protocol,
            'action': action,
        }

        if port is not None:
            payload['port'] = port

        # Add any additional kwargs (full field support)
        payload.update(kwargs)

        return self.post('/firewall/rules/set', payload)

    def list_firewall_rules(self, filter: dict = None) -> list:
        """List all firewall rules, optionally filtered"""
        params = {}
        if filter:
            params.update(filter)

        response = self.get('/firewall/rules/get', params=params)
        return response.get('rows', [])

    def get_firewall_rule(self, rule_id: str) -> dict:
        """Get a specific firewall rule by ID"""
        response = self.get(f'/firewall/rules/get/{rule_id}')
        return response.get('rule', {})

    def delete_firewall_rule(self, rule_id: str) -> dict:
        """Delete a firewall rule by ID"""
        return self.post(f'/firewall/rules/delete/{rule_id}', {})

    def update_firewall_rule(self, rule_id: str, **kwargs) -> dict:
        """Update a firewall rule (supports all OPNsense rule fields)"""
        payload = kwargs
        return self.post(f'/firewall/rules/set/{rule_id}', payload)

    # Validation helpers
    def _validate_rule_name(self, name: str) -> None:
        """Validate rule name is not empty and <= 255 chars"""
        if not name:
            raise ValidationError("Name required")
        if len(name) > 255:
            raise ValidationError("Name must be max 255 characters")

    def _validate_cidr(self, cidr: str, field_name: str) -> None:
        """Validate CIDR notation (e.g., 10.0.0.0/24)"""
        # Simple regex for CIDR: x.x.x.x/xx or ::/xx
        if not re.match(r'^[\da-fA-F:\.]+/\d+$', cidr):
            raise ValidationError(f"Invalid CIDR for {field_name}: {cidr}")

    def _validate_protocol(self, protocol: str) -> None:
        """Validate protocol is in allowed list"""
        if protocol not in self.VALID_PROTOCOLS:
            raise ValidationError(
                f"Invalid protocol: {protocol}. "
                f"Must be one of: {', '.join(self.VALID_PROTOCOLS)}"
            )

    def _validate_action(self, action: str) -> None:
        """Validate action is in allowed list"""
        if action not in self.VALID_ACTIONS:
            raise ValidationError(
                f"Invalid action: {action}. "
                f"Must be one of: {', '.join(self.VALID_ACTIONS)}"
            )

    def _validate_port(self, port: int) -> None:
        """Validate port is in valid range"""
        if port < 1 or port > 65535:
            raise ValidationError(f"Port out of range: {port}. Must be 1-65535")
