import pytest
from homelab_gitops.domain.validators import (
    YAMLSchemaValidator,
    ValidationResult,
)
from homelab_gitops.domain.models import NodeProfile

def test_validation_result():
    """ValidationResult captures success/failure."""
    result = ValidationResult(success=True, errors=[])
    assert result.success

    result = ValidationResult(success=False, errors=["Missing vcenter.datacenter"])
    assert not result.success
    assert len(result.errors) == 1

def test_yaml_schema_validator_valid_profile():
    """Valid profile passes validation."""
    profile_dict = {
        "name": "ubuntu-base",
        "vcenter": {
            "datacenter": "DC1",
            "cluster": "Cluster1",
            "datastore": "DS1",
            "network": "VM Network",
        },
        "vm_specs": {
            "cpu": 4,
            "memory": 8192,
            "disk": 50,
        },
        "deployment": {
            "tags": ["ubuntu"],
        },
    }
    profile = NodeProfile(**profile_dict)
    validator = YAMLSchemaValidator()
    result = validator.validate(profile)
    assert result.success
