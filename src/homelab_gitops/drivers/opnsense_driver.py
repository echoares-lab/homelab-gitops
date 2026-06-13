"""OPNsense Firewall and Network client driver."""

import os
import re
import time
import requests
from typing import Dict, Any, Optional, List
from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult


class OPNsenseDriver(Driver):
    """Driver for OPNsense Firewall and Network operations."""

    VALID_PROTOCOLS = ['tcp', 'udp', 'icmp', 'esp', 'ah', 'gre', 'ip']
    VALID_ACTIONS = ['pass', 'block', 'reject']

    def __init__(self):
        """Initialize OPNsenseDriver with environment variables."""
        self.url = os.getenv("OPNSENSE_URL", "").rstrip("/")
        self.key = os.getenv("OPNSENSE_KEY")
        self.secret = os.getenv("OPNSENSE_SECRET")
        self.verify = os.getenv("OPNSENSE_VERIFY", "false").lower() == "true"
        self.timeout = 10

    def validate(self) -> bool:
        """Validate OPNsense credentials and connectivity."""
        if not self.url or not self.key or not self.secret:
            raise PrerequisiteError(
                "OPNSENSE_URL, OPNSENSE_KEY, and OPNSENSE_SECRET must be set"
            )

        try:
            # Simple check: list interfaces as a connectivity test
            response = requests.get(
                f"{self.url}/network/interfaces/get",
                auth=(self.key, self.secret),
                verify=self.verify,
                timeout=self.timeout
            )
            if response.status_code == 401:
                raise PrerequisiteError("Invalid OPNsense API credentials")
            if response.status_code != 200:
                raise PrerequisiteError(
                    f"OPNsense connection failed with status: {response.status_code}"
                )
            return True
        except requests.exceptions.RequestException as e:
            raise PrerequisiteError(f"OPNsense unreachable: {str(e)}")

    def execute(self, task: Task) -> TaskResult:
        """Execute OPNsense operations for VLAN and Firewall rules."""
        start = time.time()
        
        # Determine operation from overrides or task type
        resource = task.overrides.get("resource", task.type)
        action = task.overrides.get("action", "create")
        
        try:
            if resource == "vlan":
                output = self._handle_vlan(action, task.overrides)
            elif resource == "firewall":
                output = self._handle_firewall(action, task.overrides)
            elif resource == "interface":
                output = self._handle_interface(action, task.overrides)
            elif resource == "dhcp":
                output = self._handle_dhcp(action, task.overrides)
            else:
                raise ExecutionError(f"Unsupported resource type: {resource}")

            duration = time.time() - start
            return TaskResult(
                success=True,
                task_type=task.type,
                output=output,
                duration=duration,
            )
        except Exception as e:
            raise ExecutionError(f"OPNsense operation failed: {str(e)}")

    def _handle_dhcp(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DHCP (dnsmasq) operations."""
        if action == "list_enabled":
            # Get dnsmasq settings
            settings = self._get('/dnsmasq/settings/get')
            dnsmasq = settings.get('dnsmasq', {})
            
            # Get excluded interfaces
            no_iface = dnsmasq.get('dhcp', {}).get('no_interface', {})
            excluded = {iface for iface, cfg in no_iface.items() if cfg.get('selected') == 1}
            
            # Get DHCP ranges
            ranges = dnsmasq.get('dhcp_ranges', {})
            enabled_interfaces = []
            for uuid, cfg in ranges.items():
                iface_map = cfg.get('interface', {})
                for iface, iface_cfg in iface_map.items():
                    if iface_cfg.get('selected') == 1 and iface not in excluded:
                        enabled_interfaces.append({
                            'interface': iface,
                            'range_from': cfg.get('start_addr', ''),
                            'range_to': cfg.get('end_addr', ''),
                            'uuid': uuid,
                        })
            return {"interfaces": enabled_interfaces}
            
        elif action in ["enable", "disable"]:
            interface = params.get("interface")
            if not interface:
                raise ExecutionError("Interface required for DHCP operation")
                
            # Get current excluded list
            settings = self._get('/dnsmasq/settings/get')
            no_iface = settings.get('dnsmasq', {}).get('dhcp', {}).get('no_interface', {})
            current_excluded = {iface for iface, cfg in no_iface.items() if cfg.get('selected') == 1}
            
            if action == "disable":
                current_excluded.add(interface)
            else:
                current_excluded.discard(interface)
                
            # Update settings
            payload = {
                'dnsmasq': {
                    'dhcp': {
                        'no_interface': ','.join(sorted(current_excluded))
                    }
                }
            }
            res = self._post('/dnsmasq/settings/set', payload)
            
            # Reconfigure service
            self._post('/dnsmasq/service/reconfigure', {})
            
            return res
            
        else:
            raise ExecutionError(f"Unsupported DHCP action: {action}")

    def _handle_interface(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Interface operations."""
        if action == "list":
            response = self._get('/network/interfaces/get')
            return {"interfaces": response.get('interfaces', [])}
        
        elif action == "get":
            name = params.get("name")
            if not name:
                raise ExecutionError("Interface name required")
            return self._get(f'/network/interfaces/get/{name}')
        
        elif action == "configure":
            name = params.get("name")
            if not name:
                raise ExecutionError("Interface name required")
            payload = {}
            # Add extra params for configuration
            for k, v in params.items():
                if k not in ['resource', 'action', 'name']:
                    payload[k] = v
            return self._post(f'/network/interfaces/set/{name}', payload)
        
        else:
            raise ExecutionError(f"Unsupported interface action: {action}")

    def _handle_vlan(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle VLAN operations."""
        if action == "create":
            interface = params.get("interface")
            vlan_id = params.get("vlan_id")
            description = params.get("description")

            if not interface:
                raise ExecutionError("Interface required for VLAN creation")
            if vlan_id is None or not (1 <= int(vlan_id) <= 4094):
                raise ExecutionError(f"Invalid VLAN ID: {vlan_id}. Must be 1-4094")
            if not description:
                raise ExecutionError("Description required for VLAN creation")

            payload = {
                'interface': interface,
                'vlan_id': int(vlan_id),
                'description': description,
            }
            # Add extra params
            for k, v in params.items():
                if k not in ['resource', 'action', 'interface', 'vlan_id', 'description']:
                    payload[k] = v

            return self._post('/network/vlans/set', payload)
        
        elif action == "delete":
            vlan_uuid = params.get("uuid")
            if not vlan_uuid:
                raise ExecutionError("VLAN UUID required for deletion")
            return self._post(f'/network/vlans/delete/{vlan_uuid}', {})
        
        elif action == "list":
            response = self._get('/network/vlans/get')
            return {"vlans": response.get('rows', [])}
        
        else:
            raise ExecutionError(f"Unsupported VLAN action: {action}")

    def _handle_firewall(self, action: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Handle Firewall operations."""
        if action == "create":
            name = params.get("name")
            src_net = params.get("src_net")
            dst_net = params.get("dst_net")
            protocol = params.get("protocol")
            rule_action = params.get("rule_action", "pass")
            port = params.get("port")

            self._validate_rule_name(name)
            self._validate_cidr(src_net, 'src_net')
            self._validate_cidr(dst_net, 'dst_net')
            self._validate_protocol(protocol)
            self._validate_action(rule_action)

            payload = {
                'name': name,
                'src_net': src_net,
                'dst_net': dst_net,
                'protocol': protocol,
                'action': rule_action,
            }
            if port:
                self._validate_port(int(port))
                payload['port'] = int(port)

            # Add extra params
            for k, v in params.items():
                if k not in ['resource', 'action', 'name', 'src_net', 'dst_net', 
                            'protocol', 'rule_action', 'port']:
                    payload[k] = v

            return self._post('/firewall/rules/set', payload)
            
        elif action == "delete":
            rule_uuid = params.get("uuid")
            if not rule_uuid:
                raise ExecutionError("Firewall rule UUID required for deletion")
            return self._post(f'/firewall/rules/delete/{rule_uuid}', {})
            
        elif action == "list":
            response = self._get('/firewall/rules/get')
            return {"rules": response.get('rows', [])}
            
        else:
            raise ExecutionError(f"Unsupported firewall action: {action}")

    # API Helpers
    def _get(self, endpoint: str) -> Dict[str, Any]:
        """Perform GET request."""
        response = requests.get(
            f"{self.url}{endpoint}",
            auth=(self.key, self.secret),
            verify=self.verify,
            timeout=self.timeout
        )
        return self._handle_response(response)

    def _post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Perform POST request."""
        response = requests.post(
            f"{self.url}{endpoint}",
            auth=(self.key, self.secret),
            json=data,
            verify=self.verify,
            timeout=self.timeout
        )
        return self._handle_response(response)

    def _handle_response(self, response: requests.Response) -> Dict[str, Any]:
        """Handle API response."""
        if response.status_code >= 400:
            raise ExecutionError(f"API Error ({response.status_code}): {response.text}")
        try:
            return response.json()
        except Exception:
            return {"status": "ok", "raw_response": response.text}

    # Ported Validations
    def _validate_rule_name(self, name: str) -> None:
        if not name or len(name) > 255:
            raise ExecutionError("Invalid name: must be 1-255 characters")

    def _validate_cidr(self, cidr: str, field: str) -> None:
        if not cidr or not re.match(r'^[\da-fA-F:\.]+/\d+$', cidr):
            # OPNsense also supports aliases and special values like 'any', 'lan', etc.
            # But the original code was strict. I'll stick to what was there or 
            # relax it if it makes sense. The original code used this regex.
            if cidr not in ['any', 'lan', 'wan']: # Basic common values
                 if not re.match(r'^[\da-fA-F:\.]+/\d+$', cidr):
                     raise ExecutionError(f"Invalid CIDR for {field}: {cidr}")

    def _validate_protocol(self, protocol: str) -> None:
        if protocol not in self.VALID_PROTOCOLS:
            raise ExecutionError(f"Invalid protocol: {protocol}")

    def _validate_action(self, action: str) -> None:
        if action not in self.VALID_ACTIONS:
            raise ExecutionError(f"Invalid action: {action}")

    def _validate_port(self, port: int) -> None:
        if not (1 <= port <= 65535):
            raise ExecutionError(f"Invalid port: {port}")
