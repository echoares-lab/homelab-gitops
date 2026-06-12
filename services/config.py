"""ConfigService: Manages profile, role, and playbook configuration."""

import os
import yaml
from typing import List, Tuple, Dict, Optional
from pathlib import Path
from rich.console import Console

console = Console()

# Map deployment tags to playbooks and required extra vars
PLAYBOOK_MAP = {
    "cf_runner":    ("ansible/cloudflare-runner.yml", []),
    "cf_dev":       ("ansible/cloudflare-dev.yml",    []),
    "homelab_dev":  ("ansible/homelab-dev.yml",       []),
    "combined_dev": ("ansible/combined-dev.yml",      ["github_pat"]),
    "git_test":     ("ansible/git-test-runner.yml",   []),
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
        required_fields = {"vcenter", "content_library", "vm_specs", "deployment"}

        for field in required_fields:
            if field not in profile:
                raise ValueError(f"Profile missing required section: {field}")

        # Validate vm_specs has hardware config
        specs = profile.get("vm_specs", {})
        required_hw = {"cpu", "ram_gb", "disk_size_gb"}
        for hw_field in required_hw:
            if hw_field not in specs:
                raise ValueError(f"Profile vm_specs missing: {hw_field}")

        # Validate deployment has tags
        deployment = profile.get("deployment", {})
        if "tags" not in deployment:
            raise ValueError("Profile deployment missing: tags")

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

        # If no tag matches, default to ansible/site.yml
        return "ansible/site.yml", []

    def create_profile(self, name: str, spec: dict, tags: List[str]) -> bool:
        """
        Create a new profile YAML file.

        Args:
            name: Profile name (e.g., 'ubuntu-2404-custom')
            spec: Hardware spec dict with cpu, ram_gb, disk_size_gb, etc.
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
            "vcenter": {
                "datacenter": "HOMELAB",
                "cluster": "Primary",
                "host": "esxi-01.mgmt.plexplease.com",
                "datastore": "ds-nfs-prod",
                "network": "VM Network"
            },
            "content_library": {
                "name": "GOLDEN",
                "template": "ubuntu-24.04-lts-golden"
            },
            "vm_specs": {
                "cpu": spec.get("cpu", 2),
                "ram_gb": spec.get("ram_gb", spec.get("memory", 4)),
                "guest_id": "ubuntu64Guest",
                "disk_size_gb": spec.get("disk_size_gb", spec.get("disk", 40))
            },
            "deployment": {
                "tags": tags,
                "vm_name_prefix": name.split("-")[0] if "-" in name else name,
                "vm_name_domain": "mgmt.plexplease.com"
            }
        }

        with open(profile_path, 'w') as f:
            yaml.dump(profile_content, f, default_flow_style=False, sort_keys=False)

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
