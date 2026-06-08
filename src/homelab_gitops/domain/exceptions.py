"""Domain layer exceptions."""


class DomainError(Exception):
    """Base exception for domain layer."""
    pass


class ValidationError(DomainError):
    """Profile or configuration validation failed."""
    pass


class InvalidStateTransition(DomainError):
    """Attempted invalid state transition."""
    def __init__(self, current: str, target: str):
        self.current = current
        self.target = target
        super().__init__(f"Invalid transition: {current} → {target}")


class ProvisioningError(DomainError):
    """VM provisioning failed."""
    pass


class ConfigurationError(DomainError):
    """Ansible configuration failed."""
    pass


class TestError(DomainError):
    """Testinfra validation failed."""
    pass


class InsufficientResourcesError(ProvisioningError):
    """Cluster has insufficient resources."""
    pass


class ProvisioningTimeout(ProvisioningError):
    """Provisioning took too long."""
    pass
