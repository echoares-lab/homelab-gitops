#!/usr/bin/env python3
"""
Validate Ansible playbook, role, profile, and metadata structure.
"""

import sys
from pathlib import Path
from typing import Any, Iterable

import yaml


class AnsibleStructureValidator:
    """Validates repository Ansible structure without running Ansible."""

    def __init__(self, repo_root: Path | None = None):
        self.repo_root = repo_root or Path.cwd()
        self.ansible_dir = self.repo_root / "ansible"
        self.roles_dir = self.ansible_dir / "roles"
        self.profiles_dir = self.repo_root / "config" / "profiles"
        self.metadata_file = self.repo_root / "config" / "metadata.yml"
        self.errors: list[str] = []
        self.warnings: list[str] = []
        self.successes: list[str] = []

    def _load_yaml(self, path: Path) -> Any:
        try:
            with path.open(encoding="utf-8") as handle:
                return yaml.safe_load(handle)
        except yaml.YAMLError as exc:
            self.errors.append(
                f"{path.relative_to(self.repo_root)} has invalid YAML: {exc}"
            )
            return None

    def _role_dirs(self) -> set[str]:
        if not self.roles_dir.exists():
            self.errors.append("ansible/roles directory is missing")
            return set()
        return {
            path.name
            for path in self.roles_dir.iterdir()
            if path.is_dir() and not path.name.startswith(".")
        }

    def _playbook_files(self) -> list[Path]:
        if not self.ansible_dir.exists():
            self.errors.append("ansible directory is missing")
            return []
        return sorted(self.ansible_dir.glob("*.yml"))

    def _profile_files(self) -> list[Path]:
        if not self.profiles_dir.exists():
            self.warnings.append("config/profiles directory is missing")
            return []
        return sorted(self.profiles_dir.glob("*.yml"))

    def _collect_role_names(self, node: Any) -> Iterable[str]:
        if isinstance(node, list):
            for item in node:
                yield from self._collect_role_names(item)
            return

        if not isinstance(node, dict):
            return

        roles = node.get("roles")
        if isinstance(roles, list):
            for role in roles:
                yield from self._role_name_from_entry(role)

        dependencies = node.get("dependencies")
        if isinstance(dependencies, list):
            for dependency in dependencies:
                yield from self._role_name_from_entry(dependency)

        for role_key in ("include_role", "import_role"):
            yield from self._role_name_from_task_value(node.get(role_key))

        nested_keys = (
            "tasks",
            "pre_tasks",
            "post_tasks",
            "handlers",
            "block",
            "rescue",
            "always",
        )
        for nested_key in nested_keys:
            yield from self._collect_role_names(node.get(nested_key))

    def _role_name_from_entry(self, entry: Any) -> Iterable[str]:
        if isinstance(entry, str):
            yield entry
        elif isinstance(entry, dict):
            role_name = entry.get("role") or entry.get("name")
            if isinstance(role_name, str):
                yield role_name

    def _role_name_from_task_value(self, value: Any) -> Iterable[str]:
        if isinstance(value, str):
            yield value
        elif isinstance(value, dict):
            role_name = value.get("name") or value.get("role")
            if isinstance(role_name, str):
                yield role_name

    def _normalize_role_name(self, role_name: str) -> str:
        return role_name.removeprefix("roles/").split("/", 1)[0]

    def check_playbook_role_references(self, role_dirs: set[str]) -> bool:
        missing: list[str] = []
        for playbook in self._playbook_files():
            data = self._load_yaml(playbook)
            if data is None:
                continue

            for role_name in sorted(set(self._collect_role_names(data))):
                normalized = self._normalize_role_name(role_name)
                if normalized and normalized not in role_dirs:
                    rel_playbook = playbook.relative_to(self.ansible_dir)
                    message = (
                        f"{rel_playbook} references missing role directory: "
                        f"{normalized}"
                    )
                    missing.append(message)

        if missing:
            self.errors.extend(missing)
            return False

        self.successes.append(
            "Playbook role references resolve to role directories"
        )
        return True

    def check_profile_references(self, role_dirs: set[str]) -> bool:
        missing: list[str] = []
        for profile in self._profile_files():
            data = self._load_yaml(profile)
            if not isinstance(data, dict):
                continue

            deployment = data.get("deployment") or {}
            if not isinstance(deployment, dict):
                continue

            for playbook_ref in deployment.get("playbooks") or []:
                if not isinstance(playbook_ref, str):
                    continue
                playbook_path = Path(playbook_ref)
                is_ansible_path = (
                    playbook_path.parts and playbook_path.parts[0] == "ansible"
                )
                if not is_ansible_path:
                    playbook_path = Path("ansible") / playbook_path
                if not (self.repo_root / playbook_path).exists():
                    message = (
                        f"{profile.name} references missing playbook: "
                        f"{playbook_path.as_posix()}"
                    )
                    missing.append(message)

            for role_name in deployment.get("roles") or []:
                if not isinstance(role_name, str):
                    continue
                normalized = self._normalize_role_name(role_name)
                if normalized and normalized not in role_dirs:
                    message = (
                        f"{profile.name} references missing role directory: "
                        f"{normalized}"
                    )
                    missing.append(message)

        if missing:
            self.errors.extend(missing)
            return False

        self.successes.append("Profile playbook and role references resolve")
        return True

    def check_metadata_consistency(self, role_dirs: set[str]) -> bool:
        metadata = self._load_yaml(self.metadata_file)
        if not isinstance(metadata, dict):
            self.errors.append("config/metadata.yml must contain a mapping")
            return False

        metadata_roles = metadata.get("roles") or {}
        if not isinstance(metadata_roles, dict):
            self.errors.append(
                "config/metadata.yml roles section must be a mapping"
            )
            return False

        metadata_tags = metadata.get("tags") or {}
        if not isinstance(metadata_tags, dict):
            self.errors.append(
                "config/metadata.yml tags section must be a mapping"
            )
            return False

        ok = True
        stale_roles = sorted(set(metadata_roles) - role_dirs)
        missing_metadata_roles = sorted(role_dirs - set(metadata_roles))

        for role_name in stale_roles:
            self.errors.append(
                f"metadata references missing role directory: {role_name}"
            )
            ok = False

        for role_name in missing_metadata_roles:
            self.errors.append(
                f"role directory missing metadata description: {role_name}"
            )
            ok = False

        missing_tags = sorted(self._profile_tags() - set(metadata_tags))
        for tag_name in missing_tags:
            self.errors.append(
                f"profile tag missing metadata description: {tag_name}"
            )
            ok = False

        if ok:
            self.successes.append(
                "Role and profile tag metadata is consistent"
            )
        return ok

    def _profile_tags(self) -> set[str]:
        tags: set[str] = set()
        for profile in self._profile_files():
            data = self._load_yaml(profile)
            if not isinstance(data, dict):
                continue
            deployment = data.get("deployment") or {}
            if not isinstance(deployment, dict):
                continue
            for tag in deployment.get("tags") or []:
                if isinstance(tag, str):
                    tags.add(tag)
        return tags

    def validate_all(self) -> bool:
        role_dirs = self._role_dirs()
        self.check_playbook_role_references(role_dirs)
        self.check_profile_references(role_dirs)
        self.check_metadata_consistency(role_dirs)
        return not self.errors

    def report(self) -> int:
        print("\n" + "=" * 70)
        print("Ansible Structure Validation Report")
        print("=" * 70 + "\n")

        if self.successes:
            print("Successes:")
            for success in self.successes:
                print(f"  - {success}")
            print()

        if self.warnings:
            print("Warnings:")
            for warning in self.warnings:
                print(f"  - {warning}")
            print()

        if self.errors:
            print("Errors:")
            for error in self.errors:
                print(f"  - {error}")
            print()
            print("=" * 70)
            print("Validation FAILED - Please fix the errors above")
            print("=" * 70 + "\n")
            return 1

        print("=" * 70)
        print("Validation PASSED - Ansible structure is consistent")
        print("=" * 70 + "\n")
        return 0


def main() -> None:
    validator = AnsibleStructureValidator()
    validator.validate_all()
    sys.exit(validator.report())


if __name__ == "__main__":
    main()
