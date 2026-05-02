import pytest

def test_ufw_enabled(host):
    ufw = host.service("ufw")
    assert ufw.is_running
    assert ufw.is_enabled

def test_apt_clean(host):
    # Check if there are any broken packages or pending updates that fail
    cmd = host.run("sudo apt-get -s upgrade")
    assert cmd.rc == 0
