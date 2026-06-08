"""OPNsense module clients"""

from opnsense.modules.firewall import FirewallClient
from opnsense.modules.network import NetworkClient

__all__ = ['FirewallClient', 'NetworkClient']
