"""ConfigService: Manages profile, role, and playbook configuration."""

import os
import yaml
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from rich.console import Console

console = Console()

# Map deployment tags to playbooks and required extra vars
PLAYBOOK_MAP = {
    "cf_runner":    ("cloudflare-runner.yml", ["runner_token"]),
    "cf_dev":       ("cloudflare-dev.yml",    []),
    "homelab_dev":  ("homelab-dev.yml",       []),
    "combined_dev": ("combined-dev.yml",      ["github_pat"]),
    "git_test":     ("git-test-runner.yml",   ["runner_token"]),
}

class ConfigService:
    """Manages profile, role, and playbook configuration."""

    def __init__(self, profiles_dir: str = "config/profiles", roles_dir: str = "ansible/roles"):
        self.profiles_dir = profiles_dir
        self.roles_dir = roles_dir

    def load_profile(self, profile_name: str) -> dict:
        """
        Load and parse a profile YAML file.

        Args:
            profile_name: Name of profile (e.g., 'ubuntu-2404-base')

        Returns:
            Parsed profile dictionary

        Raises:
            FileNotFoundError: If profile doesn't exist
            yaml.YAMLError: If YAML is invalid
        """
        profile_path = Path(self.profiles_dir) / f"{profile_name}.yml"

        if not profile_path.exists():
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path, 'r') as f:
            profile = yaml.safe_load(f)

        if not profile:
            raise ValueError(f"Profile {profile_name} is empty or invalid")

        return profile

    def validate_profile(self, profile: dict) -> bool:
        """
        Validate that a profile has required fields.

        Args:
            profile: Profile dictionary

        Returns:
            True if valid

        Raises:
            ValueError: If required fields missing
        """
        required_fields = {"name", "spec", "tags"}

        for field in required_fields:
            if field not in profile:
                raise ValueError(f"Profile missing required field: {field}")

        # Validate spec has hardware config
        spec = profile.get("spec", {})
        required_hw = {"cpu", "memory", "disk"}
        for hw_field in required_hw:
            if hw_field not in spec:
                raise ValueError(f"Profile spec missing: {hw_field}")

        return True

    def resolve_playbook(self, profile_name: str) -> Tuple[str, List[str]]:
        """
        Get the playbook and required extra vars for a profile based on its tags.

        Args:
            profile_name: Name of profile

        Returns:
            Tuple of (playbook_filename, list_of_required_extra_var_keys)

        Raises:
            ValueError: If no playbook found for profile's tags
        """
        profile = self.load_profile(profile_name)
        tags = profile.get("tags", [])

        for tag in tags:
            if tag in PLAYBOOK_MAP:
                playbook, extra_vars = PLAYBOOK_MAP[tag]
                return playbook, extra_vars

        # If no tag matches, default to site.yml
        return "site.yml", []

    def create_profile(self, name: str, spec: dict, tags: List[str]) -> bool:
        """
        Create a new profile YAML file.

        Args:
            name: Profile name (e.g., 'ubuntu-2404-custom')
            spec: Hardware spec dict with cpu, memory, disk, etc.
            tags: List of tags for the profile

        Returns:
            True on success

        Raises:
            FileExistsError: If profile already exists
        """
        profile_path = Path(self.profiles_dir) / f"{name}.yml"

        if profile_path.exists():
            raise FileExistsError(f"Profile already exists: {profile_path}")

        profile_content = {
            "name": name,
            "spec": spec,
            "tags": tags,
        }

        with open(profile_path, 'w') as f:
            yaml.dump(profile_content, f, default_flow_style=False)

        return True

    def create_role(self, name: str) -> bool:
        """
        Create a new Ansible role directory structure.

        Args:
            name: Role name (e.g., 'harden_os')

        Returns:
            True on success

        Raises:
            FileExistsError: If role already exists
        """
        role_dir = Path(self.roles_dir) / name

        if role_dir.exists():
            raise FileExistsError(f"Role already exists: {role_dir}")

        # Create directory structure
        (role_dir / "tasks").mkdir(parents=True)
        (role_dir / "handlers").mkdir(parents=True)
        (role_dir / "templates").mkdir(parents=True)
        (role_dir / "defaults").mkdir(parents=True)

        # Create main.yml files
        (role_dir / "tasks" / "main.yml").write_text("---\n- name: Example task\n  debug:\n    msg: Hello\n")

        return True
