import pytest
import os

def test_os_specific_packages(host):
    distro = host.system_info.distribution.lower()
    
    if distro == "ubuntu":
        # Ubuntu specific checks
        assert host.package("ufw").is_installed
        assert host.service("ufw").is_enabled
    elif distro == "photon":
        # Photon OS specific checks
        assert host.package("tdnf").is_installed
    else:
        pytest.skip(f"No specific tests for distribution: {distro}")

def test_docker_ready(host):
    profile = os.environ.get("RUNTIME_PROFILE", "").lower()
    if "docker" not in profile:
        pytest.skip("Skipping Docker check for non-docker profile")

    # Check for docker if the host has the 'docker' tag
    docker = host.package("docker-ce")
    if not docker.is_installed:
        docker = host.package("docker") # Photon uses 'docker' package
        
    if docker.is_installed:
        assert host.service("docker").is_running
        assert host.service("docker").is_enabled
    else:
        pytest.fail("Docker package expected but not installed for docker profile")

def test_technitium_ready(host):
    profile = os.environ.get("RUNTIME_PROFILE", "").lower()
    if "dns" not in profile:
        pytest.skip("Skipping Technitium check for non-dns profile")

    # Check if the dns service is running
    assert host.service("dns").is_running
    
    # Check if port 5380 is listening
    assert host.socket("tcp://0.0.0.0:5380").is_listening
