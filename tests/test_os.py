import pytest

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
    # Check for docker if the host has the 'docker' tag (passed via env or metadata if possible)
    # For now, we check if docker is installed generally on docker-tagged nodes
    docker = host.package("docker-ce")
    if not docker.is_installed:
        docker = host.package("docker") # Photon uses 'docker' package
        
    if docker.is_installed:
        assert host.service("docker").is_running
        assert host.service("docker").is_enabled
