"""Unit tests for OrchestrateService."""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
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

    @patch("services.orchestrate.TofuWrapper")
    @pytest.mark.unit
    def test_deploy_calls_tofu_wrapper(self, mock_tofu_class):
        """Test that deploy instantiates TofuWrapper and calls apply()."""
        # Create mocks
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock profile with deployment info
        mock_config.load_profile.return_value = {
            "name": "ubuntu-2404-base",
            "deployment": {
                "vm_name_prefix": "ubuntu",
                "vm_name_domain": "mgmt.plexplease.com"
            }
        }

        # Configure mock wrapper
        mock_wrapper = Mock()
        mock_wrapper.apply.return_value = True
        mock_wrapper.workspace_new.return_value = True
        mock_tofu_class.return_value = mock_wrapper

        service = OrchestrateService(mock_infra, mock_config)
        result = service.deploy("ubuntu-2404-base", "01")

        # Verify TofuWrapper was instantiated with correct workspace name
        mock_tofu_class.assert_called_once_with(workspace="ubuntu-01.mgmt.plexplease.com")

        # Verify workspace_new and apply were called
        mock_wrapper.workspace_new.assert_called_once_with("ubuntu-01.mgmt.plexplease.com")
        mock_wrapper.apply.assert_called_once()

        # Verify result is True
        assert result is True

    @patch("services.orchestrate.TofuWrapper")
    @pytest.mark.unit
    def test_deploy_returns_false_on_apply_failure(self, mock_tofu_class):
        """Test that deploy returns False when TofuWrapper.apply() fails."""
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock profile
        mock_config.load_profile.return_value = {
            "name": "ubuntu-2404-base",
            "deployment": {
                "vm_name_prefix": "ubuntu",
                "vm_name_domain": "mgmt.plexplease.com"
            }
        }

        # Configure mock wrapper to return False on apply
        mock_wrapper = Mock()
        mock_wrapper.apply.return_value = False
        mock_wrapper.workspace_new.return_value = True
        mock_tofu_class.return_value = mock_wrapper

        service = OrchestrateService(mock_infra, mock_config)
        result = service.deploy("ubuntu-2404-base", "01")

        assert result is False

    @patch("services.orchestrate.TofuWrapper")
    @pytest.mark.unit
    def test_deploy_handles_wrapper_exception(self, mock_tofu_class):
        """Test that deploy returns False when TofuWrapper raises exception."""
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock profile
        mock_config.load_profile.return_value = {
            "name": "ubuntu-2404-base",
            "deployment": {
                "vm_name_prefix": "ubuntu",
                "vm_name_domain": "mgmt.plexplease.com"
            }
        }

        # Configure mock wrapper to raise exception
        mock_tofu_class.side_effect = RuntimeError("OpenTofu not found")

        service = OrchestrateService(mock_infra, mock_config)
        result = service.deploy("ubuntu-2404-base", "01")

        assert result is False

    @pytest.mark.unit
    def test_deploy_validates_mac_address(self):
        """Test that deploy validates MAC address format."""
        mock_infra = Mock()
        mock_config = Mock()
        mock_config.load_profile.return_value = {
            "name": "ubuntu-2404-base",
            "deployment": {
                "vm_name_prefix": "ubuntu",
                "vm_name_domain": "mgmt.plexplease.com"
            }
        }

        service = OrchestrateService(mock_infra, mock_config)

        # Valid MAC should succeed (will call TofuWrapper, which we're not mocking)
        # For this test, we just verify that invalid MAC fails in validation
        result = service.deploy("ubuntu-2404-base", "01", mac="invalid-mac")
        assert result is False

    @patch("services.orchestrate.TofuWrapper")
    @pytest.mark.unit
    def test_deploy_constructs_correct_workspace_name(self, mock_tofu_class):
        """Test that deploy constructs workspace name correctly."""
        mock_infra = Mock()
        mock_config = Mock()

        # Configure mock profile
        mock_config.load_profile.return_value = {
            "name": "photon-docker",
            "deployment": {
                "vm_name_prefix": "docker",
                "vm_name_domain": "infa.plexplease.com"
            }
        }

        # Configure mock wrapper
        mock_wrapper = Mock()
        mock_wrapper.apply.return_value = True
        mock_wrapper.workspace_new.return_value = True
        mock_tofu_class.return_value = mock_wrapper

        service = OrchestrateService(mock_infra, mock_config)
        result = service.deploy("photon-docker", "03")

        # Verify correct workspace name was constructed
        mock_tofu_class.assert_called_once_with(workspace="docker-03.infa.plexplease.com")
        assert result is True

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

    @patch("services.orchestrate.TofuWrapper")
    @pytest.mark.unit
    def test_all_runs_complete_pipeline(self, mock_tofu_class):
        """Test that all() runs lint → deploy → config → test."""
        mock_infra = Mock()
        mock_config = Mock()

        # Setup mocks for the pipeline
        mock_config.load_profile.return_value = {
            "name": "ubuntu-2404-base",
            "spec": {"cpu": 2, "memory": 4, "disk": 20},
            "tags": ["docker"],
            "deployment": {
                "vm_name_prefix": "ubuntu",
                "vm_name_domain": "mgmt.plexplease.com"
            }
        }
        mock_config.validate_profile.return_value = True
        mock_config.resolve_playbook.return_value = ("site.yml", [])
        mock_infra.ensure_tags_exist.return_value = True

        # Configure mock TofuWrapper
        mock_wrapper = Mock()
        mock_wrapper.apply.return_value = True
        mock_wrapper.workspace_new.return_value = True
        mock_tofu_class.return_value = mock_wrapper

        service = OrchestrateService(mock_infra, mock_config)
        result = service.all("ubuntu-2404-base", "01", "esxi-01")

        # Verify pipeline succeeded
        assert result is True

        # Verify key methods were called
        # lint step calls these
        assert mock_config.load_profile.called
        assert mock_config.validate_profile.called
        assert mock_infra.ensure_tags_exist.called

        # deploy step calls TofuWrapper
        assert mock_tofu_class.called
        assert mock_wrapper.apply.called

        # config step calls this
        assert mock_config.resolve_playbook.called
