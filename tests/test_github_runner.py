"""
Testinfra tests for VMs provisioned with the github_runner role.
Run via manage.py test with profile ubuntu-2404-github-runner, or directly:

  pytest --hosts='ansible@<ip>' \
         --ssh-extra-args='-o StrictHostKeyChecking=no -o IdentityFile=~/.ssh/id_ed25519' \
         --sudo tests/test_github_runner.py
"""
import os
import pytest


def _is_runner_profile():
    profile = os.environ.get("RUNTIME_PROFILE", "").lower()
    return "runner" in profile or "cf-runner" in profile or "git-test" in profile


def _skip_if_not_runner():
    if not _is_runner_profile():
        pytest.skip("Skipping: not a runner profile (set RUNTIME_PROFILE=ubuntu-2404-github-runner)")


# ── User & permissions ────────────────────────────────────────────────────────

def test_runner_user_exists(host):
    _skip_if_not_runner()
    user = host.user("github-runner")
    assert user.exists
    assert user.shell == "/bin/bash"
    assert user.home == "/home/github-runner"

def test_runner_user_in_docker_group(host):
    _skip_if_not_runner()
    user = host.user("github-runner")
    assert "docker" in user.groups

# ── Runner installation ───────────────────────────────────────────────────────

def test_runner_root_directory(host):
    _skip_if_not_runner()
    d = host.file("/opt/actions-runner")
    assert d.exists
    assert d.is_directory
    assert d.user == "github-runner"

def test_runner_work_directory(host):
    _skip_if_not_runner()
    d = host.file("/opt/actions-runner/_work")
    assert d.exists
    assert d.is_directory

def test_runner_configured(host):
    _skip_if_not_runner()
    # .runner is written by config.sh after successful registration
    assert host.file("/opt/actions-runner/.runner").exists

def test_runner_binary_present(host):
    _skip_if_not_runner()
    assert host.file("/opt/actions-runner/run.sh").exists

# ── Systemd service ───────────────────────────────────────────────────────────

def test_runner_service_running(host):
    _skip_if_not_runner()
    # svc.sh names the unit actions.runner.<org>.<repo>.<name>.service
    result = host.run("systemctl list-units --type=service --state=running | grep actions.runner")
    assert result.rc == 0, "No running actions.runner.* service found"

def test_runner_service_enabled(host):
    _skip_if_not_runner()
    result = host.run("systemctl list-unit-files --type=service --state=enabled | grep actions.runner")
    assert result.rc == 0, "No enabled actions.runner.* service found"

# ── Runtime deps ──────────────────────────────────────────────────────────────

def test_go_installed(host):
    _skip_if_not_runner()
    result = host.run("/usr/local/go/bin/go version")
    assert result.rc == 0
    assert "go" in result.stdout

def test_node_installed(host):
    _skip_if_not_runner()
    result = host.run("node --version")
    assert result.rc == 0
    assert result.stdout.strip().startswith("v")

def test_npm_installed(host):
    _skip_if_not_runner()
    result = host.run("npm --version")
    assert result.rc == 0

def test_docker_running(host):
    _skip_if_not_runner()
    svc = host.service("docker")
    assert svc.is_running
    assert svc.is_enabled

def test_runner_root_filesystem_uses_400gb_disk(host):
    _skip_if_not_runner()
    result = host.run("df --output=size -BG / | awk 'NR == 2 { gsub(/G/, \"\", $1); print $1 }'")
    assert result.rc == 0
    assert int(result.stdout.strip()) >= 380

def test_build_essential_installed(host):
    _skip_if_not_runner()
    assert host.package("build-essential").is_installed

def test_jq_installed(host):
    _skip_if_not_runner()
    assert host.package("jq").is_installed

def test_direnv_installed(host):
    _skip_if_not_runner()
    assert host.package("direnv").is_installed

def test_psmisc_installed(host):
    _skip_if_not_runner()
    assert host.package("psmisc").is_installed

def test_python_venv_installed(host):
    _skip_if_not_runner()
    assert host.package("python3-venv").is_installed

# ── Writable cache dirs ───────────────────────────────────────────────────────

@pytest.mark.parametrize("path", [
    "/home/github-runner/.cache",
    "/home/github-runner/go",
    "/home/github-runner/go/pkg",
    "/home/github-runner/.npm",
])
def test_runner_cache_dir_writable(host, path):
    _skip_if_not_runner()
    d = host.file(path)
    assert d.exists
    assert d.is_directory
    assert d.user == "github-runner"
