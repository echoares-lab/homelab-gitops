import os
import pytest
import yaml
from unittest.mock import patch, MagicMock
from manage import identify_vm, resolve_playbook, PLAYBOOK_MAP, BUILD_TARGETS, app, _should_bootstrap_secrets

@patch("manage.console.status")
@patch("manage.run_cmd")
def test_identify_vm_direct_match(mock_run_cmd, mock_status):
    mock_res = MagicMock()
    mock_res.stdout = "  default\n* test-vm\n  other-vm"
    mock_res.returncode = 0
    mock_run_cmd.return_value = mock_res

    result = identify_vm("test-vm")

    assert result == "test-vm"
    mock_run_cmd.assert_called_once_with("tofu workspace list", cwd="tofu", capture=True)

@patch("manage.console.status")
@patch("manage.run_cmd")
def test_identify_vm_ip_match(mock_run_cmd, mock_status):
    def side_effect(cmd, cwd=None, capture=False):
        res = MagicMock()
        if "workspace list" in cmd:
            res.stdout = "  default\n* other-vm"
            res.returncode = 0
        elif "govc find" in cmd:
            res.stdout = "/Datacenter/vm/test-vm-folder/ip-match-vm"
            res.returncode = 0
        return res

    mock_run_cmd.side_effect = side_effect

    result = identify_vm("192.168.1.50")

    assert result == "ip-match-vm"
    assert mock_run_cmd.call_count == 2
    mock_run_cmd.assert_any_call("tofu workspace list", cwd="tofu", capture=True)
    # govc path varies by machine (shutil.which vs ./build/govc fallback);
    # assert on the IP and type flag, not the binary path.
    govc_call_args = [str(call) for call in mock_run_cmd.call_args_list]
    assert any("192.168.1.50" in c and "govc find" in c for c in govc_call_args), \
        f"Expected a govc find call with the IP address; calls were: {govc_call_args}"

@patch("manage.console.status")
@patch("manage.run_cmd")
def test_identify_vm_partial_match(mock_run_cmd, mock_status):
    def side_effect(cmd, cwd=None, capture=False):
        res = MagicMock()
        res.stdout = "  default\n* test-vm-123\n  other-vm"
        res.returncode = 0
        return res

    mock_run_cmd.side_effect = side_effect

    result = identify_vm("test-vm")

    assert result == "test-vm-123"
    assert mock_run_cmd.call_count == 2
    mock_run_cmd.assert_any_call("tofu workspace list", cwd="tofu", capture=True)

@patch("manage.console.status")
@patch("manage.run_cmd")
def test_identify_vm_no_match(mock_run_cmd, mock_status):
    def side_effect(cmd, cwd=None, capture=False):
        res = MagicMock()
        res.stdout = "  default\n* other-vm"
        res.returncode = 0
        return res

    mock_run_cmd.side_effect = side_effect

    result = identify_vm("nonexistent")

    assert result is None
    assert mock_run_cmd.call_count == 2


# ── resolve_playbook ──────────────────────────────────────────────────────────

@pytest.mark.parametrize("profile,expected_playbook", [
    ("ubuntu-2404-github-runner", "cloudflare-runner.yml"),
    ("ubuntu-2404-cf-dev",        "cloudflare-dev.yml"),
    ("ubuntu-2404-homelab-dev",   "homelab-dev.yml"),
    ("ubuntu-2404-combined-dev",  "combined-dev.yml"),
    ("ubuntu-2404-base",          "site.yml"),
    ("photon-docker",             "site.yml"),
])
def test_resolve_playbook_from_profiles(profile, expected_playbook):
    """resolve_playbook reads the profile YAML on disk and maps the tag correctly."""
    profile_path = f"config/profiles/{profile}.yml"
    if not os.path.exists(profile_path):
        pytest.skip(f"Profile not found: {profile_path}")
    playbook, _ = resolve_playbook(profile)
    assert playbook == expected_playbook, (
        f"Profile '{profile}' → expected '{expected_playbook}', got '{playbook}'"
    )

def test_resolve_playbook_unknown_returns_site_yml(tmp_path):
    """Profiles with no recognised tag fall back to site.yml."""
    p = tmp_path / "mystery.yml"
    p.write_text("deployment:\n  tags:\n    - random_unknown_tag\n")
    # Temporarily make resolve_playbook look in tmp_path
    orig = os.getcwd()
    os.chdir(tmp_path)
    try:
        playbook, required = resolve_playbook("mystery")
        assert playbook == "site.yml"
        assert required == []
    finally:
        os.chdir(orig)

@pytest.mark.parametrize("tag,expected", PLAYBOOK_MAP.items())
def test_playbook_map_values_are_tuples(tag, expected):
    """Every PLAYBOOK_MAP entry is (playbook_filename, list_of_required_vars)."""
    playbook, req_vars = expected
    assert playbook.endswith(".yml"), f"Tag '{tag}': playbook should be a .yml filename"
    assert isinstance(req_vars, list), f"Tag '{tag}': required_vars should be a list"

def test_playbook_map_files_exist():
    """Every playbook referenced in PLAYBOOK_MAP must exist in ansible/."""
    missing = []
    for tag, (playbook, _) in PLAYBOOK_MAP.items():
        path = os.path.join("ansible", playbook)
        if not os.path.exists(path):
            missing.append(path)
    assert not missing, f"Missing playbook files: {missing}"


# ── BUILD_TARGETS ─────────────────────────────────────────────────────────────

def test_build_targets_structure():
    """Each BUILD_TARGETS entry maps a name to (hcl_path, human_label)."""
    for target, (hcl, label) in BUILD_TARGETS.items():
        assert hcl.endswith(".pkr.hcl"), f"Target '{target}': expected .pkr.hcl path"
        assert isinstance(label, str) and label, f"Target '{target}': label must be non-empty string"

def test_build_targets_include_expected():
    assert "ubuntu-2404" in BUILD_TARGETS
    assert "ubuntu-2604" in BUILD_TARGETS
    assert "photon-docker" in BUILD_TARGETS


@pytest.mark.parametrize("argv,expected", [
    (["manage.py"], False),
    (["manage.py", "--help"], False),
    (["manage.py", "deploy", "--help"], False),
    (["manage.py", "lint", "photon-docker"], False),
    (["manage.py", "li", "photon-docker"], False),
    (["manage.py", "create-profile"], False),
    (["manage.py", "mkrole"], False),
    (["manage.py", "deploy", "photon-docker", "01"], True),
    (["manage.py", "all", "photon-docker", "01"], True),
])
def test_should_bootstrap_secrets(argv, expected):
    assert _should_bootstrap_secrets(argv) is expected


# ── CLI aliases ───────────────────────────────────────────────────────────────

def _registered_command_names():
    names = set()
    for cmd in app.registered_commands:
        if cmd.name is not None:
            names.add(cmd.name)
        else:
            # @app.command() without an explicit name: Typer derives it from
            # the function name by replacing underscores with hyphens.
            names.add(cmd.callback.__name__.replace("_", "-"))
    return names

@pytest.mark.parametrize("alias,canonical", [
    ("bu",        "build"),
    ("li",        "lint"),
    ("dep",       "deploy"),
    ("cfg",       "config"),
    ("ts",        "test"),
    ("rm",        "destroy"),
    ("a",         "all"),
    ("mkprofile", "create-profile"),
    ("ep",        "edit-profile"),
    ("mkrole",    "create-role"),
    ("mkplay",    "create-play"),
])
def test_alias_registered(alias, canonical):
    """Every short alias must be registered as a Typer command."""
    names = _registered_command_names()
    assert alias in names, f"Alias '{alias}' (for '{canonical}') not registered in app"

def test_canonical_commands_still_registered():
    """Aliases must not replace the canonical command names."""
    names = _registered_command_names()
    for canonical in ["build", "lint", "deploy", "config", "test", "destroy", "all",
                      "create-profile", "edit-profile", "create-role", "create-play"]:
        assert canonical in names, f"Canonical command '{canonical}' missing from app"


# ── Profile YAML integrity ────────────────────────────────────────────────────

REQUIRED_PROFILE_KEYS = [
    ("vcenter", "datacenter"),
    ("vcenter", "cluster"),
    ("vcenter", "datastore"),
    ("vcenter", "network"),
    ("vm_specs", "cpu"),
    ("vm_specs", "ram_gb"),
    ("vm_specs", "disk_size_gb"),
    ("vm_specs", "guest_id"),
    ("content_library", "name"),
    ("content_library", "template"),
    ("deployment", "tags"),
    ("deployment", "vm_name_prefix"),
    ("deployment", "vm_name_domain"),
]

def _all_profiles():
    profiles_dir = "config/profiles"
    if not os.path.isdir(profiles_dir):
        return []
    return [
        os.path.join(profiles_dir, f)
        for f in os.listdir(profiles_dir)
        if f.endswith(".yml")
    ]

@pytest.mark.parametrize("profile_path", _all_profiles())
def test_profile_has_required_keys(profile_path):
    """Every profile on disk must have all required top-level + nested keys."""
    with open(profile_path) as f:
        data = yaml.safe_load(f)
    missing = []
    for section, key in REQUIRED_PROFILE_KEYS:
        if section not in data or key not in data[section]:
            missing.append(f"{section}.{key}")
    assert not missing, f"{os.path.basename(profile_path)} missing: {missing}"

@pytest.mark.parametrize("profile_path", _all_profiles())
def test_profile_specs_are_positive(profile_path):
    """cpu, ram_gb, and disk_size_gb must all be positive integers."""
    with open(profile_path) as f:
        data = yaml.safe_load(f)
    specs = data.get("vm_specs", {})
    for field in ("cpu", "ram_gb", "disk_size_gb"):
        val = specs.get(field)
        assert isinstance(val, int) and val > 0, (
            f"{os.path.basename(profile_path)}: vm_specs.{field} must be a positive int, got {val!r}"
        )
