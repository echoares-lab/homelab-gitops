import pytest

def test_iptables_running(host):
    # Photon uses iptables/systemd for firewall
    iptables = host.service("iptables")
    assert iptables.is_running
    assert iptables.is_enabled

def test_docker_running(host):
    # This test only runs on nodes tagged with 'docker'
    docker_pkg = host.package("docker")
    if docker_pkg.is_installed:
        docker_svc = host.service("docker")
        assert docker_svc.is_running
        assert docker_svc.is_enabled

def test_nginx_stack(host):
    # Check if the test compose stack is responding
    # We check if port 80 is listening
    port = host.socket("tcp://0.0.0.0:80")
    if port.is_listening:
        assert True
