import yaml
from pathlib import Path


def test_log_retention_defaults_are_bounded():
    defaults_file = Path("ansible/roles/log_retention/defaults/main.yml")
    with open(defaults_file) as f:
        defaults = yaml.safe_load(f)

    assert defaults["log_retention_rotate_count"] == 14
    assert defaults["log_retention_max_size"] == "100M"
    assert defaults["log_retention_journald_vacuum_time"] == "14d"
    assert defaults["log_retention_journald_vacuum_size"] == "512M"


def test_log_retention_tasks_install_policy_files():
    tasks_file = Path("ansible/roles/log_retention/tasks/main.yml")
    with open(tasks_file) as f:
        tasks = yaml.safe_load(f)

    task_names = [task.get("name") for task in tasks if isinstance(task, dict)]
    assert "Configure profile logrotate policy" in task_names
    assert "Install journald vacuum service" in task_names
    assert "Install journald vacuum timer" in task_names
    assert "Enable journald vacuum timer" in task_names


def test_log_retention_logrotate_template_uses_profile_paths():
    template = Path("ansible/roles/log_retention/templates/profile-logrotate.j2").read_text()

    assert "log_retention_files" in template
    assert "maxsize" in template
    assert "copytruncate" in template


def test_photon_dns_profile_sets_technitium_log_policy():
    with open("config/profiles/photon-dns.yml") as f:
        profile = yaml.safe_load(f)

    logging_cfg = profile["logging"]
    assert logging_cfg["files"][0]["path"] == "/var/log/technitium/dns/*.log"
    assert logging_cfg["files"][0]["rotate_count"] == 14
    assert logging_cfg["journald"]["vacuum_size"] == "512M"
