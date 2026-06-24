from pathlib import Path

from scripts.validate_ansible_structure import AnsibleStructureValidator


def write_yaml(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validator_accepts_matching_roles_playbooks_and_metadata(tmp_path):
    write_yaml(
        tmp_path / "ansible" / "site.yml",
        """---
- name: Configure hosts
  hosts: all
  roles:
    - base
    - role: docker
""",
    )
    write_yaml(
        tmp_path / "ansible" / "roles" / "base" / "tasks" / "main.yml",
        "---\n- debug:\n    msg: base\n",
    )
    write_yaml(
        tmp_path / "ansible" / "roles" / "docker" / "tasks" / "main.yml",
        "---\n- debug:\n    msg: docker\n",
    )
    write_yaml(
        tmp_path / "config" / "metadata.yml",
        """---
roles:
  base: Core host setup.
  docker: Docker runtime setup.
tags: {}
commands: {}
""",
    )

    validator = AnsibleStructureValidator(tmp_path)

    assert validator.validate_all()
    assert not validator.errors


def test_validator_catches_missing_role_directories(tmp_path):
    write_yaml(
        tmp_path / "ansible" / "site.yml",
        """---
- name: Configure hosts
  hosts: all
  roles:
    - base
    - missing_role
""",
    )
    write_yaml(
        tmp_path / "ansible" / "roles" / "base" / "tasks" / "main.yml",
        "---\n- debug:\n    msg: base\n",
    )
    write_yaml(
        tmp_path / "config" / "metadata.yml",
        """---
roles:
  base: Core host setup.
  missing_role: Stale role.
tags: {}
commands: {}
""",
    )

    validator = AnsibleStructureValidator(tmp_path)

    assert not validator.validate_all()
    assert any(
        "site.yml references missing role directory: missing_role" in error
        for error in validator.errors
    )


def test_validator_catches_stale_metadata_role_references(tmp_path):
    write_yaml(
        tmp_path / "ansible" / "site.yml",
        """---
- name: Configure hosts
  hosts: all
  roles:
    - base
""",
    )
    write_yaml(
        tmp_path / "ansible" / "roles" / "base" / "tasks" / "main.yml",
        "---\n- debug:\n    msg: base\n",
    )
    write_yaml(
        tmp_path / "config" / "metadata.yml",
        """---
roles:
  base: Core host setup.
  removed_role: This role no longer exists.
tags: {}
commands: {}
""",
    )

    validator = AnsibleStructureValidator(tmp_path)

    assert not validator.validate_all()
    assert any(
        "metadata references missing role directory: removed_role" in error
        for error in validator.errors
    )


def test_validator_catches_missing_profile_playbook_references(tmp_path):
    write_yaml(
        tmp_path / "ansible" / "site.yml",
        """---
- name: Configure hosts
  hosts: all
  roles:
    - base
""",
    )
    write_yaml(
        tmp_path / "ansible" / "roles" / "base" / "tasks" / "main.yml",
        "---\n- debug:\n    msg: base\n",
    )
    write_yaml(
        tmp_path / "config" / "metadata.yml",
        """---
roles:
  base: Core host setup.
tags: {}
commands: {}
""",
    )
    write_yaml(
        tmp_path / "config" / "profiles" / "example.yml",
        """---
deployment:
  playbooks:
    - site.yml
    - missing.yml
""",
    )

    validator = AnsibleStructureValidator(tmp_path)

    assert not validator.validate_all()
    assert any(
        "example.yml references missing playbook: ansible/missing.yml" in error
        for error in validator.errors
    )
