"""Unit tests for InfrastructureService."""

import pytest
from unittest.mock import Mock, patch
from services.infrastructure import InfrastructureService

class TestInfrastructureServiceEnsureTags:
    """Test InfrastructureService.ensure_tags_exist()."""

    @pytest.mark.unit
    def test_ensure_tags_returns_true_for_empty_list(self):
        """Test that empty tag list returns True immediately."""
        service = InfrastructureService()
        result = service.ensure_tags_exist([])
        assert result is True

    @pytest.mark.unit
    def test_ensure_tags_handles_missing_govc(self):
        """Test that service handles missing govc gracefully."""
        service = InfrastructureService()
        # govc might not exist, which is fine for unit tests
        assert service.govc_path is not None

class TestInfrastructureServiceGetHostInfo:
    """Test InfrastructureService.get_host_info()."""

    @pytest.mark.unit
    def test_get_host_info_returns_dict(self):
        """Test that get_host_info returns a dictionary."""
        service = InfrastructureService()
        result = service.get_host_info("esxi-01.example.com")

        assert isinstance(result, dict)
        assert "name" in result
        assert result["name"] == "esxi-01.example.com"

class TestInfrastructureServiceRunAnsiblePlaybook:
    """Test InfrastructureService.run_ansible_playbook()."""

    @pytest.mark.unit
    @patch('services.infrastructure.run_cmd')
    def test_run_ansible_playbook_builds_command(self, mock_run_cmd):
        """Test that run_ansible_playbook builds correct command."""
        mock_run_cmd.return_value = (0, "", "")

        service = InfrastructureService()
        service.run_ansible_playbook(
            "ansible/site.yml",
            "10.10.10.50,",
            extra_vars={"host_var": "value"}
        )

        # Verify run_cmd was called with ansible-playbook
        mock_run_cmd.assert_called_once()
        call_args = mock_run_cmd.call_args[0][0]
        assert "ansible-playbook" in call_args
        assert "10.10.10.50," in call_args

class TestInfrastructureServiceValidateAnsible:
    """Test InfrastructureService.validate_ansible_syntax()."""

    @pytest.mark.unit
    @patch('services.infrastructure.run_cmd')
    def test_validate_ansible_syntax_calls_syntax_check(self, mock_run_cmd):
        """Test that syntax validation uses --syntax-check."""
        mock_run_cmd.return_value = (0, "", "")

        service = InfrastructureService()
        result = service.validate_ansible_syntax("ansible/site.yml")

        assert result is True
        call_args = mock_run_cmd.call_args[0][0]
        assert "--syntax-check" in call_args
