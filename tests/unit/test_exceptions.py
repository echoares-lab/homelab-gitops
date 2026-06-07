import pytest
from homelab_gitops.domain.exceptions import (
    DomainError,
    ValidationError,
    InvalidStateTransition,
    ProvisioningError,
)

def test_domain_error_is_exception():
    """Domain errors are Exceptions."""
    error = DomainError("Test error")
    assert isinstance(error, Exception)

def test_invalid_state_transition_error():
    """InvalidStateTransition captures state info."""
    error = InvalidStateTransition("planned", "tested")
    assert "planned" in str(error)
    assert "tested" in str(error)
