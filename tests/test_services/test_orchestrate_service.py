"""Unit tests for OrchestrateService."""

import pytest
from unittest.mock import Mock, MagicMock, patch
from services.orchestrate import OrchestrateService

class TestOrchestrateServiceBuild:
    """Test OrchestrateService.build()."""

    @patch("services.orchestrate.PackerWrapper")
    @pytest.mark.unit
    def test_build_calls_packer_wrapper_build(self, mock_packer_class):
        """Test that build instantiates PackerWrapper and calls build()."""
        # Create mocks
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock wrapper
        mock_wrapper = Mock()
        mock_wrapper.build.return_value = True
        mock_packer_class.return_value = mock_wrapper

        service = OrchestrateService(mock_infra, mock_config)
        result = service.build("ubuntu-2404")

        # Verify PackerWrapper was instantiated
        mock_packer_class.assert_called_once()

        # Verify build was called with correct target
        mock_wrapper.build.assert_called_once_with("ubuntu-2404")

        # Verify result is True
        assert result is True

    @patch("services.orchestrate.PackerWrapper")
    @pytest.mark.unit
    def test_build_returns_false_on_wrapper_failure(self, mock_packer_class):
        """Test that build returns False when PackerWrapper.build() fails."""
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock wrapper to return False
        mock_wrapper = Mock()
        mock_wrapper.build.return_value = False
        mock_packer_class.return_value = mock_wrapper

        service = OrchestrateService(mock_infra, mock_config)
        result = service.build("ubuntu-2404")

        assert result is False

    @patch("services.orchestrate.PackerWrapper")
    @pytest.mark.unit
    def test_build_handles_wrapper_exception(self, mock_packer_class):
        """Test that build returns False when PackerWrapper raises exception."""
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock wrapper to raise exception
        mock_packer_class.side_effect = RuntimeError("Packer not found")

        service = OrchestrateService(mock_infra, mock_config)
        result = service.build("ubuntu-2404")

        assert result is False

    @patch("services.orchestrate.PackerWrapper")
    @pytest.mark.unit
    def test_build_handles_different_targets(self, mock_packer_class):
        """Test that build works with different target names."""
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock wrapper
        mock_wrapper = Mock()
        mock_wrapper.build.return_value = True
        mock_packer_class.return_value = mock_wrapper

        service = OrchestrateService(mock_infra, mock_config)

        # Test with different targets
        for target in ["ubuntu-2404", "ubuntu-2604", "photon-docker"]:
            result = service.build(target)
            assert result is True
            # Verify correct target was passed
            assert target in [call[0][0] for call in mock_wrapper.build.call_args_list]

class TestOrchestrateServiceLint:
    """Test OrchestrateService.lint()."""

    @pytest.mark.unit
    def test_lint_loads_and_validates_profile(self):
        """Test that lint loads and validates a profile."""
        # Create mocks
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock to return valid profile
        mock_config.load_profile.return_value = {
            "name": "ubuntu-2404-base",
            "spec": {"cpu": 2, "memory": 4, "disk": 20},
            "tags": ["docker"]
        }
        mock_config.validate_profile.return_value = True
        mock_infra.ensure_tags_exist.return_value = True

        service = OrchestrateService(mock_infra, mock_config)
        result = service.lint("ubuntu-2404-base", "01")

        # Verify calls
        mock_config.load_profile.assert_called_once_with("ubuntu-2404-base")
        mock_config.validate_profile.assert_called_once()
        mock_infra.ensure_tags_exist.assert_called_once()
        assert result is True

    @pytest.mark.unit
    def test_lint_returns_false_on_profile_not_found(self):
        """Test that lint returns False if profile doesn't exist."""
        mock_infra = Mock()
        mock_config = Mock()
        mock_config.load_profile.side_effect = FileNotFoundError("Profile not found")

        service = OrchestrateService(mock_infra, mock_config)
        result = service.lint("nonexistent", "01")

        assert result is False

class TestOrchestrateServiceDeploy:
    """Test OrchestrateService.deploy()."""

    @pytest.mark.unit
    def test_deploy_validates_mac_address(self):
        """Test that deploy validates MAC address format."""
        mock_infra = Mock()
        mock_config = Mock()
        mock_config.load_profile.return_value = {"name": "test"}

        service = OrchestrateService(mock_infra, mock_config)

        # Valid MAC should succeed
        result = service.deploy("ubuntu-2404-base", "01", mac="00:11:22:33:44:55")
        assert result is True

        # Invalid MAC should return False (caught by exception handler)
        result = service.deploy("ubuntu-2404-base", "01", mac="invalid-mac")
        assert result is False

class TestOrchestrateServiceStatus:
    """Test OrchestrateService.status()."""

    @pytest.mark.unit
    def test_status_returns_fleet_list(self):
        """Test that status returns list of VM statuses."""
        mock_infra = Mock()
        mock_config = Mock()

        fleet_data = [
            {"name": "ubuntu-2404-base-01", "power": "on", "ip": "10.10.10.50"},
            {"name": "ubuntu-2404-base-02", "power": "off", "ip": "10.10.10.51"},
        ]
        mock_infra.collect_fleet_status.return_value = fleet_data

        service = OrchestrateService(mock_infra, mock_config)
        result = service.status()

        assert isinstance(result, list)
        assert len(result) == 2
        assert result[0]["name"] == "ubuntu-2404-base-01"

class TestOrchestrateServiceAll:
    """Test OrchestrateService.all() (complete pipeline)."""

    @pytest.mark.unit
    def test_all_runs_complete_pipeline(self):
        """Test that all() runs lint → deploy → config → test."""
        mock_infra = Mock()
        mock_config = Mock()

        # Setup mocks for the pipeline
        mock_config.load_profile.return_value = {
            "name": "ubuntu-2404-base",
            "spec": {"cpu": 2, "memory": 4, "disk": 20},
            "tags": ["docker"]
        }
        mock_config.validate_profile.return_value = True
        mock_config.resolve_playbook.return_value = ("site.yml", [])
        mock_infra.ensure_tags_exist.return_value = True

        service = OrchestrateService(mock_infra, mock_config)
        result = service.all("ubuntu-2404-base", "01", "esxi-01")

        # Verify pipeline succeeded
        assert result is True

        # Verify key methods were called
        # lint step calls these
        assert mock_config.load_profile.called
        assert mock_config.validate_profile.called
        assert mock_infra.ensure_tags_exist.called

        # config step calls this
        assert mock_config.resolve_playbook.called
