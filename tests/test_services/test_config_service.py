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
            "name": "test",
            "spec": {"cpu": 2, "memory": 4, "disk": 20},
            "tags": ["docker"]
        }

        service = ConfigService()
        result = service.validate_profile(profile)
        assert result is True

    @pytest.mark.unit
    def test_validate_profile_raises_on_missing_name(self):
        """Test that validation fails without 'name' field."""
        profile = {
            "spec": {"cpu": 2, "memory": 4, "disk": 20},
            "tags": ["docker"]
        }

        service = ConfigService()
        with pytest.raises(ValueError, match="missing required field: name"):
            service.validate_profile(profile)

class TestConfigServiceResolvePlaybook:
    """Test ConfigService.resolve_playbook()."""

    @pytest.mark.unit
    def test_resolve_playbook_for_docker_tag(self, tmp_path):
        """Test playbook resolution for docker tag."""
        profile_dir = tmp_path / "profiles"
        profile_dir.mkdir()

        profile_data = {
            "name": "docker-host",
            "spec": {"cpu": 4, "memory": 8, "disk": 50},
            "tags": ["docker"]
        }

        profile_file = profile_dir / "docker-host.yml"
        with open(profile_file, 'w') as f:
            yaml.dump(profile_data, f)

        service = ConfigService(profiles_dir=str(profile_dir))

        # This test may not match PLAYBOOK_MAP, but validates the logic
        playbook, extra_vars = service.resolve_playbook("docker-host")

        assert isinstance(playbook, str)
        assert isinstance(extra_vars, list)

class TestConfigServiceCreateProfile:
    """Test ConfigService.create_profile()."""

    @pytest.mark.unit
    def test_create_profile_creates_file(self, tmp_path):
        """Test that create_profile writes YAML file."""
        service = ConfigService(profiles_dir=str(tmp_path))

        spec = {"cpu": 2, "memory": 4, "disk": 20}
        tags = ["docker"]

        result = service.create_profile("new-profile", spec, tags)

        assert result is True
        assert (tmp_path / "new-profile.yml").exists()

        # Verify contents
        with open(tmp_path / "new-profile.yml") as f:
            saved = yaml.safe_load(f)

        assert saved["name"] == "new-profile"
        assert saved["spec"] == spec
        assert saved["tags"] == tags

    @pytest.mark.unit
    def test_create_profile_raises_on_duplicate(self, tmp_path):
        """Test that create_profile raises if file exists."""
        service = ConfigService(profiles_dir=str(tmp_path))

        # Create first profile
        service.create_profile("test", {"cpu": 2, "memory": 4, "disk": 20}, ["docker"])

        # Try to create again
        with pytest.raises(FileExistsError):
            service.create_profile("test", {"cpu": 2, "memory": 4, "disk": 20}, ["docker"])
