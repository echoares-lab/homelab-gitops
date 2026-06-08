import pytest
import yaml
from pathlib import Path


@pytest.fixture
def alloy_defaults():
    """Load Alloy role defaults."""
    defaults_file = Path("ansible/roles/alloy/defaults/main.yml")
    with open(defaults_file) as f:
        return yaml.safe_load(f)


@pytest.fixture
def alloy_config_template():
    """Load Alloy config template."""
    template_file = Path("ansible/roles/alloy/templates/alloy-config.river")
    with open(template_file) as f:
        return f.read()


def test_alloy_defaults_has_prometheus_url(alloy_defaults):
    """Alloy defaults should specify central Prometheus URL."""
    assert "alloy_central_prometheus_url" in alloy_defaults
    assert alloy_defaults["alloy_central_prometheus_url"] == "http://10.10.10.30:9090"


def test_alloy_defaults_has_loki_url(alloy_defaults):
    """Alloy defaults should specify central Loki URL."""
    assert "alloy_central_loki_url" in alloy_defaults
    assert alloy_defaults["alloy_central_loki_url"] == "http://10.10.10.30:3100"


def test_alloy_defaults_has_scrape_interval(alloy_defaults):
    """Alloy defaults should specify scrape interval."""
    assert "alloy_scrape_interval" in alloy_defaults
    assert alloy_defaults["alloy_scrape_interval"] == "15s"


def test_alloy_defaults_skip_alloy_flag(alloy_defaults):
    """Alloy defaults should have alloy_skip flag for opt-out."""
    assert "alloy_skip" in alloy_defaults
    assert alloy_defaults["alloy_skip"] is False


def test_alloy_config_has_prometheus_scrape(alloy_config_template):
    """Alloy config template should include Prometheus scrape config."""
    assert "prometheus.scrape" in alloy_config_template
    assert "prometheus.remote_write" in alloy_config_template


def test_alloy_config_has_loki_write(alloy_config_template):
    """Alloy config template should include Loki write config."""
    assert "loki.write" in alloy_config_template


def test_alloy_config_conditional_docker_metrics(alloy_config_template):
    """Alloy config should conditionally include Docker metrics when enabled."""
    assert "alloy_enable_docker_metrics" in alloy_config_template
    assert "prometheus.scrape \"docker\"" in alloy_config_template


def test_alloy_tasks_has_main_file():
    """Alloy role tasks/main.yml should exist."""
    tasks_file = Path("ansible/roles/alloy/tasks/main.yml")
    assert tasks_file.exists()


def test_alloy_handlers_has_restart():
    """Alloy handlers should include restart Alloy service handler."""
    handlers_file = Path("ansible/roles/alloy/handlers/main.yml")
    with open(handlers_file) as f:
        handlers = yaml.safe_load(f)

    handler_names = [h.get("name") for h in handlers]
    assert "Restart Alloy service" in handler_names
