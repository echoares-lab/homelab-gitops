import pytest
import os

def test_ansible_user_exists(host):
    user = host.user("ansible")
    assert user.exists

def test_ansible_sudo_privileges(host):
    # Verify the ansible user can execute sudo without a password
    assert host.run("sudo -n true").rc == 0

def test_ssh_hardened(host):
    sshd_config = host.file("/etc/ssh/sshd_config").content_string
    assert "PermitRootLogin no" in sshd_config
    assert "PasswordAuthentication no" in sshd_config

def test_python3_installed(host):
    python = host.package("python3")
    assert python.is_installed

def test_mac_address(host):
    expected_mac = os.environ.get("EXPECTED_MAC")
    if expected_mac:
        # Normalize MAC to lowercase for comparison
        expected_mac = expected_mac.lower()
        # Get all MAC addresses from the system
        res = host.run("ip link show")
        assert expected_mac in res.stdout.lower(), f"Expected MAC {expected_mac} not found in 'ip link show' output"
