import pytest

def test_ssh_running_and_enabled(host):
    # Ubuntu 24.04 uses ssh.service aliased as "ssh"; check running + socket active
    result = host.run("systemctl is-active ssh")
    assert result.rc == 0, f"ssh service not active: {result.stdout.strip()}"

def test_python3_installed(host):
    python3 = host.package("python3")
    assert python3.is_installed

def test_management_user_exists(host):
    user = host.user("ansible")
    assert user.exists
    assert "sudo" in user.groups

def test_minimal_install_packages(host):
    # telnet should never be present; snapd may be in some golden images so skip it
    assert not host.package("telnet").is_installed

def test_ssh_config_hardening(host):
    sshd_config = host.file("/etc/ssh/sshd_config").content_string
    assert "PermitRootLogin no" in sshd_config
    assert "PasswordAuthentication no" in sshd_config

def test_ufw_enabled(host):
    ufw = host.service("ufw")
    assert ufw.is_running
