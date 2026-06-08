import pytest
import yaml
import json
from pathlib import Path


@pytest.fixture
def docker_metrics_defaults():
    """Load Docker metrics role defaults."""
    defaults_file = Path("ansible/roles/docker_metrics/defaults/main.yml")
    with open(defaults_file) as f:
        return yaml.safe_load(f)


@pytest.fixture
def docker_metrics_certs():
    """Check that TLS cert files exist."""
    cert_files = [
        Path("ansible/roles/docker_metrics/files/ca.crt"),
        Path("ansible/roles/docker_metrics/files/server.crt"),
        Path("ansible/roles/docker_metrics/files/server.key"),
    ]
    return cert_files


def test_docker_metrics_defaults_enabled(docker_metrics_defaults):
    """Docker metrics should be enabled by default."""
    assert "docker_metrics_enabled" in docker_metrics_defaults
    assert docker_metrics_defaults["docker_metrics_enabled"] is True


def test_docker_metrics_tls_port(docker_metrics_defaults):
    """Docker metrics should specify TLS port."""
    assert "docker_metrics_tls_port" in docker_metrics_defaults
    assert docker_metrics_defaults["docker_metrics_tls_port"] == 2376


def test_docker_metrics_cert_path(docker_metrics_defaults):
    """Docker metrics should specify cert directory path."""
    assert "docker_metrics_cert_path" in docker_metrics_defaults
    assert docker_metrics_defaults["docker_metrics_cert_path"] == "/etc/docker/certs.d"


def test_docker_metrics_tasks_exist():
    """Docker metrics role tasks/main.yml should exist."""
    tasks_file = Path("ansible/roles/docker_metrics/tasks/main.yml")
    assert tasks_file.exists()


def test_docker_metrics_tasks_create_cert_dir():
    """Docker metrics tasks should create cert directory."""
    tasks_file = Path("ansible/roles/docker_metrics/tasks/main.yml")
    with open(tasks_file) as f:
        tasks = yaml.safe_load(f)

    task_names = [t.get("name") for t in tasks if isinstance(t, dict)]
    assert "Create Docker certs directory" in task_names


def test_docker_metrics_tasks_distribute_certs():
    """Docker metrics tasks should distribute TLS certificates."""
    tasks_file = Path("ansible/roles/docker_metrics/tasks/main.yml")
    with open(tasks_file) as f:
        tasks = yaml.safe_load(f)

    task_names = [t.get("name") for t in tasks if isinstance(t, dict)]
    assert "Distribute CA certificate" in task_names
    assert "Distribute server certificate" in task_names
    assert "Distribute server key" in task_names


def test_docker_metrics_tasks_update_daemon_config():
    """Docker metrics tasks should update Docker daemon config."""
    tasks_file = Path("ansible/roles/docker_metrics/tasks/main.yml")
    with open(tasks_file) as f:
        tasks = yaml.safe_load(f)

    task_names = [t.get("name") for t in tasks if isinstance(t, dict)]
    assert "Update Docker daemon config for TLS and metrics" in task_names


def test_docker_metrics_handlers_restart():
    """Docker metrics handlers should include restart Docker daemon."""
    handlers_file = Path("ansible/roles/docker_metrics/handlers/main.yml")
    with open(handlers_file) as f:
        handlers = yaml.safe_load(f)

    handler_names = [h.get("name") for h in handlers]
    assert "Restart Docker daemon" in handler_names


def test_docker_metrics_cert_files_exist(docker_metrics_certs):
    """TLS certificate files should exist (as placeholders)."""
    for cert_file in docker_metrics_certs:
        assert cert_file.exists(), f"Certificate file {cert_file} not found"


def test_docker_metrics_cert_files_have_content(docker_metrics_certs):
    """TLS certificate files should have placeholder content."""
    for cert_file in docker_metrics_certs:
        with open(cert_file) as f:
            content = f.read()
        assert len(content) > 0, f"Certificate file {cert_file} is empty"
        assert "PLACEHOLDER" in content, f"Certificate file {cert_file} should contain PLACEHOLDER"
