import pytest

def test_ansible_user_exists(host):
    user = host.user("ansible")
    assert user.exists
    assert "sudo" in user.groups or "wheel" in user.groups

def test_ssh_hardened(host):
    sshd_config = host.file("/etc/ssh/sshd_config").content_string
    assert "PermitRootLogin no" in sshd_config
    assert "PasswordAuthentication no" in sshd_config

def test_python3_installed(host):
    python = host.package("python3")
    assert python.is_installed
