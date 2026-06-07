import pytest
from unittest.mock import patch, MagicMock
from homelab_gitops.drivers.ansible_driver import AnsibleDriver
from homelab_gitops.domain.models import Task, NodeProfile


def test_ansible_driver_validate():
    """AnsibleDriver validates ansible is installed."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/ansible-playbook"
        driver = AnsibleDriver()
        assert driver.validate()


def test_ansible_driver_validate_missing():
    """AnsibleDriver raises if ansible not found."""
    from homelab_gitops.drivers.exceptions import PrerequisiteError
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        driver = AnsibleDriver()
        with pytest.raises(PrerequisiteError):
            driver.validate()
