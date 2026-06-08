"""
Services module for Unified HomeLab GitOps Orchestrator.

Contains business logic extracted from manage.py:
- SecretsService: 1Password secrets bootstrapping
- ConfigService: Profile/role/playbook management
- InfrastructureService: vCenter, OpenTofu, Ansible integration
- OrchestrateService: VM lifecycle orchestration
- DNSService: Technetium DNS integration
- utils: Shared utility functions
"""

from services.secrets import SecretsService

# Lazy imports for services still in development
__all__ = [
    "SecretsService",
]

try:
    from services.config import ConfigService
    __all__.append("ConfigService")
except ImportError:
    pass

try:
    from services.infrastructure import InfrastructureService
    __all__.append("InfrastructureService")
except ImportError:
    pass

try:
    from services.orchestrate import OrchestrateService
    __all__.append("OrchestrateService")
except ImportError:
    pass

try:
    from services.dns import DNSService
    __all__.append("DNSService")
except ImportError:
    pass
