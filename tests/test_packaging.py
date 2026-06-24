"""Packaging configuration smoke tests."""

from pathlib import Path
import tomllib
import yaml


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


def test_ci_builds_and_smoke_tests_installed_package():
    workflow = yaml.safe_load(Path(".github/workflows/lint-and-unit-tests.yml").read_text())

    run_blocks = "\n".join(
        step.get("run", "")
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
    )

    assert "python -m build --sdist --wheel" in run_blocks
    assert "python -m venv /tmp/homelab-gitops-clean-install" in run_blocks
    assert "pip install dist/*.whl" in run_blocks
    assert "/tmp/homelab-gitops-clean-install/bin/homelab-gitops --help" in run_blocks
    assert "/tmp/homelab-gitops-clean-install/bin/homelab-gitops doctor --help" in run_blocks
