"""Validators for domain models."""

from dataclasses import dataclass
from typing import List
from homelab_gitops.domain.models import NodeProfile


@dataclass
class ValidationResult:
    """Result of validation."""
    success: bool
    errors: List[str]


class Validator:
    """Base class for validators."""
    def validate(self, profile: NodeProfile) -> ValidationResult:
        """Validate a profile. Override in subclasses."""
        raise NotImplementedError


class YAMLSchemaValidator(Validator):
    """Validate profile YAML against schema."""

    def validate(self, profile: NodeProfile) -> ValidationResult:
        """Validate NodeProfile has required structure."""
        errors = []

        required_vcenter = ["datacenter", "cluster", "datastore", "network"]
        for key in required_vcenter:
            if key not in profile.vcenter or not profile.vcenter[key]:
                errors.append(f"vcenter.{key} is required")

        required_vm = ["cpu", "memory", "disk"]
        for key in required_vm:
            if key not in profile.vm_specs or profile.vm_specs[key] is None:
                errors.append(f"vm_specs.{key} is required")

        if "tags" not in profile.deployment:
            errors.append("deployment.tags is required")

        return ValidationResult(success=len(errors) == 0, errors=errors)


class TagValidator(Validator):
    """Validate that deployment tags are valid."""

    VALID_TAGS = {"ubuntu", "photon", "docker", "dns", "runner"}

    def validate(self, profile: NodeProfile) -> ValidationResult:
        """Validate tags are known."""
        errors = []
        tags = profile.deployment.get("tags", [])

        for tag in tags:
            if tag not in self.VALID_TAGS:
                errors.append(f"Unknown tag: {tag}")

        return ValidationResult(success=len(errors) == 0, errors=errors)
