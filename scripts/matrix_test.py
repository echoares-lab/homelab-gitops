import subprocess
import os
import sys
import time
import yaml
import pexpect
import shlex
from dataclasses import dataclass, field
from typing import List

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    _RICH = True
    _console = Console()
except ImportError:
    _RICH = False
    _console = None

# Configuration
TEST_PROFILE = "matrix-test-node"
TEST_IP = "10.10.10.119"
TEST_GW = "10.10.10.1"

EXPECTED_ALIASES = {
    "bu": "build", "li": "lint", "dep": "deploy", "cfg": "config",
    "ts": "test", "rm": "destroy", "st": "status", "a": "all",
    "mkprofile": "create-profile", "ep": "edit-profile",
    "mkrole": "create-role", "mkplay": "create-play",
}

CANONICAL_COMMANDS = [
    "build", "lint", "deploy", "config", "test", "destroy", "status", "all",
    "create-profile", "edit-profile", "create-role", "create-play",
]

KNOWN_PROFILES = [
    "ubuntu-2404-base",
    "ubuntu-2404-cf-dev",
    "ubuntu-2404-github-runner",
    "ubuntu-2404-homelab-dev",
    "ubuntu-2404-combined-dev",
    "ubuntu-2404-git-test",
]

PROFILE_TAG_TO_PLAYBOOK = {
    "cf_runner":    "cloudflare-runner.yml",
    "cf_dev":       "cloudflare-dev.yml",
    "homelab_dev":  "homelab-dev.yml",
    "combined_dev": "combined-dev.yml",
    "git_test":     "git-test-runner.yml",
}

REQUIRED_PROFILE_KEYS = [
    ("vcenter",         "datacenter"),
    ("vcenter",         "cluster"),
    ("vcenter",         "datastore"),
    ("vcenter",         "network"),
    ("vm_specs",        "cpu"),
    ("vm_specs",        "ram_gb"),
    ("vm_specs",        "disk_size_gb"),
    ("vm_specs",        "guest_id"),
    ("content_library", "name"),
    ("content_library", "template"),
    ("deployment",      "tags"),
    ("deployment",      "vm_name_prefix"),
    ("deployment",      "vm_name_domain"),
]


class MatrixTestFailed(Exception):
    pass


@dataclass
class TestResult:
    name: str
    status: str        # "PASS" | "FAIL" | "SKIP"
    duration: float
    error: str = ""


@dataclass
class ResultTracker:
    results: List[TestResult] = field(default_factory=list)

    def record(self, name: str, status: str, duration: float, error: str = ""):
        self.results.append(TestResult(name, status, duration, error))

    def print_summary(self):
        if _RICH:
            _print_rich_summary(self.results)
        else:
            _print_plain_summary(self.results)
        failed = [r for r in self.results if r.status == "FAIL"]
        return len(failed)


def _print_rich_summary(results: List[TestResult]):
    console = _console
    console.print()

    table = Table(
        title="Matrix Test Results",
        box=box.ROUNDED,
        title_style="bold cyan",
        show_footer=True,
    )
    table.add_column("Test",    style="cyan",  no_wrap=False, footer="[bold]TOTAL[/bold]")
    table.add_column("Status",  justify="center", no_wrap=True)
    table.add_column("Time",    style="dim",   justify="right", no_wrap=True)

    passed = failed = 0
    total_t = 0.0
    for r in results:
        total_t += r.duration
        if r.status == "PASS":
            passed += 1
            status_cell = "[bold green]✓ PASS[/bold green]"
            row_style = ""
        elif r.status == "FAIL":
            failed += 1
            status_cell = "[bold red]✗ FAIL[/bold red]"
            row_style = "on dark_red"
        else:
            status_cell = "[yellow]- SKIP[/yellow]"
            row_style = ""
        table.add_row(r.name, status_cell, f"{r.duration:.2f}s", style=row_style)

    summary_cell = (
        f"[bold green]{passed} passed[/bold green]"
        + (f"  [bold red]{failed} failed[/bold red]" if failed else "")
    )
    table.columns[1].footer = summary_cell
    table.columns[2].footer = f"[bold]{total_t:.2f}s[/bold]"

    console.print(table)

    failures = [r for r in results if r.status == "FAIL"]
    if failures:
        console.print()
        fail_table = Table(
            title="Failure Details",
            box=box.SIMPLE_HEAVY,
            title_style="bold red",
            show_lines=True,
        )
        fail_table.add_column("Test",   style="red",   no_wrap=False)
        fail_table.add_column("Error",  style="white", no_wrap=False)
        for r in failures:
            short = r.error.splitlines()[0][:200] if r.error else "—"
            fail_table.add_row(r.name, short)
        console.print(fail_table)


def _print_plain_summary(results: List[TestResult]):
    print("\n" + "=" * 60)
    print("MATRIX TEST RESULTS")
    print("=" * 60)
    for r in results:
        mark = "PASS" if r.status == "PASS" else ("FAIL" if r.status == "FAIL" else "SKIP")
        print(f"  [{mark}]  {r.name}  ({r.duration:.2f}s)")
    passed = sum(1 for r in results if r.status == "PASS")
    failed = sum(1 for r in results if r.status == "FAIL")
    total_t = sum(r.duration for r in results)
    print("=" * 60)
    print(f"  {passed} passed  {failed} failed  {total_t:.2f}s total")
    print("=" * 60)


_tracker = ResultTracker()


def log(msg):
    print(f"\n[MATRIX TEST] {msg}")

def fail(msg):
    print(f"[FAIL] {msg}")
    raise MatrixTestFailed(msg)

def run_cmd(cmd):
    print(f"  Running: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    res = subprocess.run(cmd, shell=False, text=True, capture_output=True)
    if res.returncode != 0:
        print(f"  STDOUT: {res.stdout}")
        print(f"  STDERR: {res.stderr}")
        fail(f"Command failed (exit {res.returncode}): {' '.join(cmd)}")
    return res.stdout


def _run_test(name: str, fn):
    """Run a single test function and record the result."""
    t0 = time.time()
    try:
        fn()
        _tracker.record(name, "PASS", time.time() - t0)
    except MatrixTestFailed as exc:
        _tracker.record(name, "FAIL", time.time() - t0, str(exc))
    except Exception as exc:
        _tracker.record(name, "FAIL", time.time() - t0, str(exc))


# ── Original tests ────────────────────────────────────────────────────────────

def test_generators():
    log("Testing Generators...")
    if os.path.exists(f"config/profiles/{TEST_PROFILE}.yml"):
        os.remove(f"config/profiles/{TEST_PROFILE}.yml")

    child = pexpect.spawn("python3 manage.py create-profile")
    child.expect("Enter new profile name:")
    child.sendline(TEST_PROFILE)
    child.expect("Base OS")
    child.sendline("1")
    child.expect("CPU Count")
    child.sendline("2")
    child.expect("RAM")
    child.sendline("4")
    child.expect("Disk Size")
    child.sendline("20")
    child.expect("Extra Tags")
    child.sendline("docker")
    child.expect(pexpect.EOF)

    if not os.path.exists(f"config/profiles/{TEST_PROFILE}.yml"):
        fail("Profile generation produced no file.")
    log("Generator test PASSED.")

def test_logic_audit():
    log("Testing Orchestrator Logic...")
    out = run_cmd(["python3", "manage.py", "lint", TEST_PROFILE, "01"])
    if "Infrastructure Linting Passed" not in out:
        fail("Linting did not report success.")
    out = run_cmd(["python3", "manage.py", "--help"])
    if "Synthesis" not in out:
        fail("--help output missing expected content.")
    log("Logic audit PASSED.")


# ── Alias tests ───────────────────────────────────────────────────────────────

def test_aliases_in_help():
    log("Testing CLI aliases appear in --help...")
    out = run_cmd(["python3", "manage.py", "--help"])
    missing = [alias for alias in EXPECTED_ALIASES if alias not in out]
    if missing:
        fail(f"Aliases missing from --help: {missing}")
    log("Alias help test PASSED.")

def test_aliases_have_help():
    log("Testing each alias responds to --help...")
    for alias, canonical in EXPECTED_ALIASES.items():
        out = run_cmd(["python3", "manage.py", alias, "--help"])
        if not out.strip():
            fail(f"Alias '{alias}' (for '{canonical}') returned empty --help")
    log("Alias --help test PASSED.")

def test_bu_alias():
    log("Testing 'bu' alias for build...")
    out = run_cmd(["python3", "manage.py", "bu", "--help"])
    if "build" not in out.lower() and "packer" not in out.lower():
        fail("'bu --help' does not look like build output")
    log("bu alias test PASSED.")


# ── Profile integrity tests ───────────────────────────────────────────────────

def test_known_profiles_exist():
    log("Testing known profiles exist on disk...")
    missing = [p for p in KNOWN_PROFILES
               if not os.path.exists(f"config/profiles/{p}.yml")]
    if missing:
        fail(f"Missing profile files: {[f'{p}.yml' for p in missing]}")
    log("Known profiles exist PASSED.")

def test_all_profiles_valid_yaml():
    log("Testing all profiles are valid YAML with required keys...")
    profiles_dir = "config/profiles"
    errors = []
    for fname in os.listdir(profiles_dir):
        if not fname.endswith(".yml"):
            continue
        path = os.path.join(profiles_dir, fname)
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
        except yaml.YAMLError as e:
            errors.append(f"{fname}: YAML parse error — {e}")
            continue
        for section, key in REQUIRED_PROFILE_KEYS:
            if section not in data or key not in (data.get(section) or {}):
                errors.append(f"{fname}: missing {section}.{key}")
    if errors:
        fail("Profile validation errors:\n  " + "\n  ".join(errors))
    log("Profile YAML integrity test PASSED.")

def test_all_profiles_positive_specs():
    log("Testing all profiles have positive vm_specs...")
    profiles_dir = "config/profiles"
    errors = []
    for fname in os.listdir(profiles_dir):
        if not fname.endswith(".yml"):
            continue
        with open(os.path.join(profiles_dir, fname)) as f:
            data = yaml.safe_load(f)
        specs = data.get("vm_specs", {})
        for field in ("cpu", "ram_gb", "disk_size_gb"):
            val = specs.get(field)
            if not isinstance(val, int) or val <= 0:
                errors.append(f"{fname}: vm_specs.{field} = {val!r} (must be positive int)")
    if errors:
        fail("\n  ".join(errors))
    log("Profile specs test PASSED.")


# ── Playbook routing tests ────────────────────────────────────────────────────

def test_playbook_files_exist():
    log("Testing all mapped playbook files exist...")
    missing = []
    for tag, playbook in PROFILE_TAG_TO_PLAYBOOK.items():
        path = os.path.join("ansible", playbook)
        if not os.path.exists(path):
            missing.append(path)
    if missing:
        fail(f"Missing playbook files: {missing}")
    log("Playbook files test PASSED.")

def test_playbook_routing():
    log("Testing profile → playbook routing...")
    errors = []
    tag_map = PROFILE_TAG_TO_PLAYBOOK
    for fname in os.listdir("config/profiles"):
        if not fname.endswith(".yml"):
            continue
        with open(os.path.join("config/profiles", fname)) as f:
            data = yaml.safe_load(f)
        tags = data.get("deployment", {}).get("tags", [])
        for tag in tags:
            if tag in tag_map:
                expected = tag_map[tag]
                actual_path = os.path.join("ansible", expected)
                if not os.path.exists(actual_path):
                    errors.append(f"{fname}: tag '{tag}' → '{expected}' not found at {actual_path}")
    if errors:
        fail("\n  ".join(errors))
    log("Playbook routing test PASSED.")


# ── Metadata drift tests ─────────────────────────────────────────────────────

def _load_metadata():
    with open("config/metadata.yml") as f:
        return yaml.safe_load(f) or {}


def test_command_metadata_coverage():
    log("Testing command metadata coverage...")
    metadata = _load_metadata()
    commands = metadata.get("commands", {})
    missing = [cmd for cmd in CANONICAL_COMMANDS if not commands.get(cmd)]
    if missing:
        fail(f"Missing command metadata: {missing}")
    log("Command metadata coverage PASSED.")


def test_profile_tag_metadata_coverage():
    log("Testing profile tag metadata coverage...")
    metadata = _load_metadata()
    known_tags = metadata.get("tags", {})
    errors = []
    for fname in os.listdir("config/profiles"):
        if not fname.endswith(".yml"):
            continue
        with open(os.path.join("config/profiles", fname)) as f:
            data = yaml.safe_load(f) or {}
        for tag in data.get("deployment", {}).get("tags", []) or []:
            if not known_tags.get(tag):
                errors.append(f"{fname}: tag '{tag}' has no metadata")
    if errors:
        fail("\n  ".join(errors))
    log("Profile tag metadata coverage PASSED.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log("Starting Matrix Testing Suite...")
    start = time.time()

    try:
        _run_test("generators",              test_generators)
        _run_test("logic_audit",             test_logic_audit)
        _run_test("aliases_in_help",         test_aliases_in_help)
        _run_test("aliases_have_help",       test_aliases_have_help)
        _run_test("bu_alias",                test_bu_alias)
        _run_test("known_profiles_exist",    test_known_profiles_exist)
        _run_test("all_profiles_valid_yaml", test_all_profiles_valid_yaml)
        _run_test("all_profiles_pos_specs",  test_all_profiles_positive_specs)
        _run_test("playbook_files_exist",    test_playbook_files_exist)
        _run_test("playbook_routing",        test_playbook_routing)
        _run_test("command_metadata",        test_command_metadata_coverage)
        _run_test("profile_tag_metadata",    test_profile_tag_metadata_coverage)
    finally:
        if os.path.exists(f"config/profiles/{TEST_PROFILE}.yml"):
            os.remove(f"config/profiles/{TEST_PROFILE}.yml")

    failures = _tracker.print_summary()
    duration = int(time.time() - start)
    log(f"Matrix Testing Suite finished in {duration}s")
    if failures:
        sys.exit(1)

if __name__ == "__main__":
    main()
