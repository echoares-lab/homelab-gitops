"""
Testinfra tests for dev workstation VMs.
Profile-gated: tests activate based on RUNTIME_PROFILE env var.

  RUNTIME_PROFILE=ubuntu-2404-cf-dev       → cf-dev checks
  RUNTIME_PROFILE=ubuntu-2404-homelab-dev  → homelab-dev checks
  RUNTIME_PROFILE=ubuntu-2404-combined-dev → all checks

Run directly:
  RUNTIME_PROFILE=ubuntu-2404-combined-dev \
  pytest --hosts='ansible@<ip>' \
         --ssh-extra-args='-o StrictHostKeyChecking=no -o IdentityFile=~/.ssh/id_ed25519' \
         --sudo tests/test_dev.py
"""
import os
import pytest

_PROFILE = os.environ.get("RUNTIME_PROFILE", "").lower()

def _is_cf_dev():
    return any(t in _PROFILE for t in ("cf-dev", "cf_dev", "combined"))

def _is_homelab_dev():
    return any(t in _PROFILE for t in ("homelab-dev", "homelab_dev", "combined"))

def _is_combined():
    return "combined" in _PROFILE

def _skip_unless(condition, reason):
    if not condition:
        pytest.skip(f"Skipping: {reason} (RUNTIME_PROFILE={_PROFILE or 'not set'})")


# ── Shared baseline (all dev profiles) ───────────────────────────────────────

def test_git_installed(host):
    _skip_unless(_is_cf_dev() or _is_homelab_dev(), "not a dev profile")
    assert host.package("git").is_installed

def test_curl_installed(host):
    _skip_unless(_is_cf_dev() or _is_homelab_dev(), "not a dev profile")
    assert host.package("curl").is_installed

def test_make_installed(host):
    _skip_unless(_is_cf_dev() or _is_homelab_dev(), "not a dev profile")
    result = host.run("which make")
    assert result.rc == 0

def test_python3_installed(host):
    _skip_unless(_is_cf_dev() or _is_homelab_dev(), "not a dev profile")
    assert host.package("python3").is_installed


# ── Cloudflare Access dev tools ───────────────────────────────────────────────

def test_go_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("/usr/local/go/bin/go version")
    assert result.rc == 0
    assert "go" in result.stdout

def test_node_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("node --version")
    assert result.rc == 0
    assert result.stdout.strip().startswith("v")

def test_gh_cli_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("gh --version")
    assert result.rc == 0
    assert "gh version" in result.stdout

def test_golangci_lint_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("golangci-lint version")
    assert result.rc == 0

def test_actionlint_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("which actionlint")
    assert result.rc == 0

def test_shellcheck_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    assert host.package("shellcheck").is_installed

def test_pre_commit_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("pre-commit --version")
    assert result.rc == 0

def test_sqlite3_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("which sqlite3")
    assert result.rc == 0

def test_docker_running(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    svc = host.service("docker")
    assert svc.is_running
    assert svc.is_enabled

def test_gopls_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("which gopls")
    assert result.rc == 0

def test_delve_installed(host):
    _skip_unless(_is_cf_dev(), "not a cf-dev or combined profile")
    result = host.run("which dlv")
    assert result.rc == 0


# ── Homelab-gitops dev tools ──────────────────────────────────────────────────

def test_opentofu_installed(host):
    _skip_unless(_is_homelab_dev(), "not a homelab-dev or combined profile")
    result = host.run("tofu version")
    assert result.rc == 0
    assert "OpenTofu" in result.stdout

def test_packer_installed(host):
    _skip_unless(_is_homelab_dev(), "not a homelab-dev or combined profile")
    result = host.run("packer version")
    assert result.rc == 0

def test_govc_installed(host):
    _skip_unless(_is_homelab_dev(), "not a homelab-dev or combined profile")
    result = host.run("govc version")
    assert result.rc == 0

def test_ansible_installed(host):
    _skip_unless(_is_homelab_dev(), "not a homelab-dev or combined profile")
    result = host.run("ansible --version")
    assert result.rc == 0

@pytest.mark.parametrize("pkg", ["typer", "rich", "yaml", "pexpect"])
def test_homelab_python_packages(host, pkg):
    _skip_unless(_is_homelab_dev(), "not a homelab-dev or combined profile")
    result = host.run(f"python3 -c 'import {pkg}'")
    assert result.rc == 0, f"Python package '{pkg}' not importable"


# ── Combined-dev: developer user, sudo, SSH key, repos ───────────────────────

def test_developer_user_exists(host):
    _skip_unless(_is_combined(), "not a combined-dev profile")
    user = host.user("developer")
    assert user.exists
    assert user.shell == "/bin/bash"
    assert "sudo" in user.groups

def test_passwordless_sudo_for_developer(host):
    _skip_unless(_is_combined(), "not a combined-dev profile")
    result = host.run("sudo -n -u developer sudo true")
    # Simpler: check the sudoers.d file exists and is correct mode
    f = host.file("/etc/sudoers.d/99-nopasswd")
    assert f.exists
    assert f.mode == 0o440
    assert "%sudo ALL=(ALL:ALL) NOPASSWD: ALL" in f.content_string

def test_developer_authorized_keys(host):
    _skip_unless(_is_combined(), "not a combined-dev profile")
    ak = host.file("/home/developer/.ssh/authorized_keys")
    assert ak.exists
    assert ak.mode == 0o600
    # Must contain at least one key
    assert len(ak.content_string.strip()) > 0

def test_repos_directory_exists(host):
    _skip_unless(_is_combined(), "not a combined-dev profile")
    d = host.file("/home/developer/repos")
    assert d.exists
    assert d.is_directory
    assert d.user == "developer"

@pytest.mark.parametrize("repo", ["cloudflare_access_automation", "homelab-gitops"])
def test_repo_cloned(host, repo):
    _skip_unless(_is_combined(), "not a combined-dev profile")
    d = host.file(f"/home/developer/repos/{repo}")
    assert d.exists
    assert d.is_directory
    # .git directory confirms it's a real clone
    git_dir = host.file(f"/home/developer/repos/{repo}/.git")
    assert git_dir.exists

def test_gh_cli_authenticated(host):
    _skip_unless(_is_combined(), "not a combined-dev profile")
    result = host.run("su - developer -c 'gh auth status'")
    assert result.rc == 0
    assert "Logged in" in result.stdout or "Logged in" in result.stderr
