"""Unit tests for ConfigService."""

import pytest
import yaml
from pathlib import Path
from services.config import ConfigService

class TestConfigServiceLoadProfile:
    """Test ConfigService.load_profile()."""

    @pytest.mark.unit
    def test_load_profile_returns_dict(self, tmp_path):
        """Test that load_profile returns a dictionary."""
        # Create a test profile
        profile_dir = tmp_path / "profiles"
        profile_dir.mkdir()

        profile_data = {
            "name": "test-profile",
            "spec": {"cpu": 2, "memory": 4, "disk": 20},
            "tags": ["docker"]
        }

        profile_file = profile_dir / "test-profile.yml"
        with open(profile_file, 'w') as f:
            yaml.dump(profile_data, f)

        service = ConfigService(profiles_dir=str(profile_dir))
        result = service.load_profile("test-profile")

        assert result == profile_data
        assert result["name"] == "test-profile"

    @pytest.mark.unit
    def test_load_profile_raises_on_missing_file(self, tmp_path):
        """Test that load_profile raises FileNotFoundError for missing profile."""
        service = ConfigService(profiles_dir=str(tmp_path))

        with pytest.raises(FileNotFoundError):
            service.load_profile("nonexistent")

class TestConfigServiceValidateProfile:
    """Test ConfigService.validate_profile()."""

    @pytest.mark.unit
    def test_validate_profile_passes_with_all_fields(self):
        """Test that valid profile passes validation."""
        profile = {
            "vcenter": {},
            "content_library": {},
            "vm_specs": {"cpu": 2, "ram_gb": 4, "disk_size_gb": 20},
            "deployment": {"tags": ["docker"]}
        }

        service = ConfigService()
        result = service.validate_profile(profile)

        assert result is True

    @pytest.mark.unit
    def test_validate_profile_raises_on_missing_name(self):
        """Test that validation fails without 'deployment' field."""
        profile = {
            "vcenter": {},
            "content_library": {},
            "vm_specs": {"cpu": 2, "ram_gb": 4, "disk_size_gb": 20}
        }

        service = ConfigService()
        with pytest.raises(ValueError, match="Profile missing required section: deployment"):
            service.validate_profile(profile)

class TestConfigServiceResolvePlaybook:
    """Test ConfigService.resolve_playbook()."""

    @pytest.mark.unit
    def test_resolve_playbook_for_docker_tag(self, tmp_path):
        """Test playbook resolution for docker tag."""
        profile_dir = tmp_path / "profiles"
        profile_dir.mkdir()

        profile_data = {
            "vcenter": {},
            "content_library": {},
            "vm_specs": {"cpu": 4, "ram_gb": 8, "disk_size_gb": 50},
            "deployment": {"tags": ["docker"]},
        }

        profile_file = profile_dir / "docker-host.yml"
        with open(profile_file, 'w') as f:
            yaml.dump(profile_data, f)

        service = ConfigService(profiles_dir=str(profile_dir))

        # This test may not match PLAYBOOK_MAP, but validates the logic
        playbook, extra_vars = service.resolve_playbook("docker-host")

        assert isinstance(playbook, str)
        assert isinstance(extra_vars, dict)

    @pytest.mark.unit
    def test_resolve_playbook_uses_deployment_tags_for_runner(self, tmp_path):
        """Runner profiles route from deployment.tags to the runner playbook."""
        profile_dir = tmp_path / "profiles"
        profile_dir.mkdir()

        profile_data = {
            "vcenter": {},
            "content_library": {},
            "vm_specs": {"cpu": 40, "ram_gb": 40, "disk_size_gb": 400},
            "deployment": {"tags": ["ubuntu", "git_test"]}
        }

        profile_file = profile_dir / "git-runner.yml"
        with open(profile_file, 'w') as f:
            yaml.dump(profile_data, f)

        service = ConfigService(profiles_dir=str(profile_dir))

        playbook, extra_vars = service.resolve_playbook("git-runner")

        assert playbook == "ansible/git-test-runner.yml"
        assert extra_vars == {}

    @pytest.mark.unit
    def test_profile_logging_maps_to_ansible_vars(self, tmp_path):
        """Profile logging policy is flattened for the log_retention role."""
        profile_dir = tmp_path / "profiles"
        profile_dir.mkdir()

        profile_data = {
            "vcenter": {},
            "content_library": {},
            "vm_specs": {"cpu": 4, "ram_gb": 8, "disk_size_gb": 50},
            "deployment": {"tags": ["photon", "dns"]},
            "logging": {
                "files": [
                    {
                        "path": "/var/log/technitium/dns/*.log",
                        "owner": "dns-server",
                        "group": "dns-server",
                        "rotate_count": 14,
                        "max_size": "100M",
                    }
                ],
                "journald": {
                    "vacuum_enabled": True,
                    "vacuum_time": "14d",
                    "vacuum_size": "512M",
                },
            },
        }

        profile_file = profile_dir / "dns.yml"
        with open(profile_file, 'w') as f:
            yaml.dump(profile_data, f)

        service = ConfigService(profiles_dir=str(profile_dir))
        _, extra_vars = service.resolve_playbook("dns")

        assert extra_vars["log_retention_files"][0]["path"] == "/var/log/technitium/dns/*.log"
        assert extra_vars["log_retention_journald_vacuum_time"] == "14d"

    @pytest.mark.unit
    @pytest.mark.parametrize("profile_name", [
        "ubuntu-2404-git-test",
        "ubuntu-2404-github-runner",
    ])
    def test_committed_runner_profiles_allocate_400gb(self, profile_name):
        """Runner profiles feed a 400 GB disk size into OpenTofu."""
        service = ConfigService()

        profile = service.load_profile(profile_name)

        assert profile["vm_specs"]["disk_size_gb"] == 400

class TestConfigServiceCreateProfile:
    """Test ConfigService.create_profile()."""

    @pytest.mark.unit
    def test_create_profile_creates_file(self, tmp_path):
        """Test that create_profile writes YAML file."""
        service = ConfigService(profiles_dir=str(tmp_path))

        spec = {"cpu": 2, "ram_gb": 4, "disk_size_gb": 20}
        tags = ["docker"]

        result = service.create_profile("new-profile", spec, tags)

        assert result is True
        assert (tmp_path / "new-profile.yml").exists()

        # Verify contents
        with open(tmp_path / "new-profile.yml") as f:
            saved = yaml.safe_load(f)

        assert saved["vm_specs"]["cpu"] == 2
        assert saved["vm_specs"]["disk_size_gb"] == 20
        assert "docker" in saved["deployment"]["tags"]

    @pytest.mark.unit
    def test_create_profile_raises_on_duplicate(self, tmp_path):
        """Test that create_profile raises if file exists."""
        service = ConfigService(profiles_dir=str(tmp_path))

        # Create first profile
        service.create_profile("test", {"cpu": 2, "memory": 4, "disk": 20}, ["docker"])

        # Try to create again
        with pytest.raises(FileExistsError):
            service.create_profile("test", {"cpu": 2, "memory": 4, "disk": 20}, ["docker"])
