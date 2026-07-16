import importlib.util
from pathlib import Path
import sys

import pytest
import yaml

from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.network import NetworkService


MODULE_PATH = (
    Path(__file__).parents[1]
    / "ansible/roles/k3s_deadman/files/k3s_deadman.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("k3s_deadman", MODULE_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def deadman():
    return load_module()


def test_watchdog_payload_requires_firing_watchdog(deadman):
    valid = {
        "status": "firing",
        "alerts": [{"status": "firing", "labels": {"alertname": "Watchdog"}}],
    }
    assert deadman.valid_watchdog_payload(valid)
    assert not deadman.valid_watchdog_payload({"status": "resolved", "alerts": []})
    assert not deadman.valid_watchdog_payload(
        {"status": "firing", "alerts": [{"labels": {"alertname": "Other"}}]}
    )


def test_state_machine_alerts_after_deadline_and_repeats_hourly(deadman):
    state = deadman.State(armed=True, last_heartbeat=100.0)
    assert deadman.transition(state, 699.0) == (state, None)

    state, event = deadman.transition(state, 700.0)
    assert event == "critical"
    state = deadman.mark_sent(state, "critical", 700.0)

    assert deadman.transition(state, 4299.0) == (state, None)
    _, event = deadman.transition(state, 4300.0)
    assert event == "critical"


def test_heartbeat_after_alert_sends_one_recovery(deadman):
    state = deadman.State(
        armed=True,
        last_heartbeat=100.0,
        alert_active=True,
        last_notification=700.0,
    )
    state = deadman.record_heartbeat(state, 800.0)
    state, event = deadman.transition(state, 800.0)
    assert event == "recovery"
    state = deadman.mark_sent(state, "recovery", 800.0)
    assert deadman.transition(state, 801.0) == (state, None)


def test_disarmed_state_never_alerts(deadman):
    state = deadman.State(armed=False, last_heartbeat=0.0)
    assert deadman.transition(state, 10_000.0) == (state, None)


def test_metrics_report_heartbeat_age_and_counters(deadman):
    state = deadman.State(
        armed=True,
        last_heartbeat=100.0,
        accepted_heartbeats=3,
        rejected_heartbeats=2,
        ses_successes=1,
        ses_failures=4,
    )
    metrics = deadman.render_metrics(state, 160.0)
    assert "k3s_deadman_heartbeat_age_seconds 60" in metrics
    assert "k3s_deadman_armed 1" in metrics
    assert "k3s_deadman_heartbeats_total{result=\"accepted\"} 3" in metrics
    assert "k3s_deadman_ses_total{result=\"failure\"} 4" in metrics


def test_deadman_profile_is_minimal_and_pinned_to_esxi03():
    profile = yaml.safe_load(
        (Path(__file__).parents[1] / "config/profiles/k3s-deadman.yml").read_text()
    )
    assert profile["vcenter"]["host"] == "10.10.10.13"
    assert profile["vcenter"]["network"] == "VM Network"
    assert profile["content_library"]["template"] == "photon-mcp"
    assert profile["vm_specs"] == {
        "cpu": 1,
        "memory": 1024,
        "disk": 50,
        "guest_id": "vmwarePhoton64Guest",
    }
    assert profile["deployment"]["tags"] == ["photon", "k3s_deadman"]
    assert "ip_address" not in profile["deployment"]
    assert profile["deployment"]["dhcp_only"] is True
    dns = (Path(__file__).parents[1] / "config/dns_records.csv").read_text()
    assert "dhcp_lease,k3s-deadman-01,10.10.10.0,,10.10.10.51" in dns


def test_deadman_network_reservation_does_not_enable_guest_static_customization():
    root = Path(__file__).parents[1]
    data = yaml.safe_load((root / "config/profiles/k3s-deadman.yml").read_text())
    data["name"] = "k3s-deadman"
    profile = NodeProfile(**data)

    NetworkService(str(root / "config/dns_records.csv")).ensure_network(profile, "01")

    assert profile.deployment["mac_address"] == "00:50:56:2d:55:01"
    assert "ip_address" not in profile.deployment


def test_vm_module_enables_manual_mac_when_profile_supplies_one():
    module = (
        Path(__file__).parents[1] / "tofu/modules/vm/main.tf"
    ).read_text()
    assert 'use_static_mac = var.mac_address != ""' in module


def test_deadman_systemd_unit_is_hardened_and_disarmed_by_default():
    root = Path(__file__).parents[1] / "ansible/roles/k3s_deadman/templates"
    unit = (root / "k3s-deadman.service.j2").read_text()
    assert "NoNewPrivileges=true" in unit
    assert "ProtectSystem=strict" in unit
    assert "LoadCredentialEncrypted=" in unit
    assert "--state /var/lib/k3s-deadman/state.json" in unit
    assert deadman_default_is_disarmed()


def deadman_default_is_disarmed():
    return load_module().State().armed is False


def test_deadman_role_encrypts_credentials_and_restricts_network_access():
    role = Path(__file__).parents[1] / "ansible/roles/k3s_deadman"
    tasks = (role / "tasks/main.yml").read_text()
    firewall = (role / "templates/k3s-deadman-firewall.service.j2").read_text()
    assert "systemd-creds" in tasks
    assert "encrypt" in tasks
    assert "Disable inherited application services" in tasks
    assert "10.10.10.50/32 -p tcp --dport 9443" in firewall
    assert "10.10.10.50/32 -p tcp --dport 9101" in firewall
    assert "10.10.10.0/24 -p tcp --dport 22" in firewall
    assert "--dport 9443 -j REJECT" in firewall
    assert "--dport 9101 -j REJECT" in firewall


def test_autostart_helper_targets_esxi03_and_deadman_vm():
    helper = (
        Path(__file__).parents[1] / "scripts/configure_k3s_deadman_autostart.sh"
    ).read_text()
    assert "10.10.10.13" in helper
    assert "k3s-deadman-01.infra.plexplease.com" in helper
    assert "govc host.autostart.add" in helper
