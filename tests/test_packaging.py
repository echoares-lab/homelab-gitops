"""Packaging configuration smoke tests."""

from pathlib import Path
import tomllib


def load_pyproject() -> dict:
    return tomllib.loads(Path("pyproject.toml").read_text())


def test_setuptools_discovers_all_homelab_gitops_packages():
    pyproject = load_pyproject()

    package_finder = pyproject["tool"]["setuptools"]["packages"]["find"]

    assert package_finder["where"] == ["src"]
    assert package_finder["include"] == ["homelab_gitops*"]


def test_console_script_invokes_existing_cli_main():
    pyproject = load_pyproject()

    assert pyproject["project"]["scripts"]["homelab-gitops"] == "homelab_gitops.cli:main"
