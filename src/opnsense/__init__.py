"""OPNsense API client library"""

from opnsense.modules.firewall import FirewallClient
from opnsense.modules.network import NetworkClient
from opnsense.exceptions import (
    OPNsenseError,
    AuthenticationError,
    APIError,
    ValidationError,
    ConfigError,
)

__version__ = "0.1.0"
__all__ = [
    'FirewallClient',
    'NetworkClient',
    'OPNsenseError',
    'AuthenticationError',
    'APIError',
    'ValidationError',
    'ConfigError',
]
