"""Wrapper classes for tool integration (OpenTofu, Ansible, testinfra, Packer)."""

from services.wrappers.base_wrapper import BaseWrapper
from services.wrappers.testinfra_wrapper import TestinfraWrapper

__all__ = [
    "BaseWrapper",
    "TestinfraWrapper",
]
