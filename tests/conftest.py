import time
import pytest
from collections import defaultdict

try:
    from rich.console import Console
    from rich.table import Table
    from rich import box
    _RICH = True
except ImportError:
    _RICH = False


def pytest_collection_modifyitems(config, items):
    """Auto-skip testinfra tests (those using the 'host' fixture) when no
    --hosts is provided. Without an explicit target they default to localhost,
    which will always fail for VM-specific assertions (ansible user, SSH
    hardening, etc.).

    To run testinfra tests against a real VM:
        pytest --hosts='ansible@<ip>' \\
               --ssh-extra-args='-o StrictHostKeyChecking=no -o IdentityFile=~/.ssh/id_ed25519' \\
               --sudo tests/<test_file>.py
    """
    has_hosts = bool(config.getoption("hosts", default=None))
    if not has_hosts:
        skip = pytest.mark.skip(
            reason="testinfra test — requires --hosts='ansible@<ip>' to target a VM"
        )
        for item in items:
            if "host" in getattr(item, "fixturenames", []):
                item.add_marker(skip)


class RichReporter:
    """Pytest plugin that prints a per-module summary table after the run."""

    def __init__(self):
        self._modules = defaultdict(lambda: {"passed": 0, "failed": 0, "skipped": 0, "duration": 0.0})
        self._failures = []
        self._start = {}

    def pytest_runtest_logstart(self, nodeid, location):
        self._start[nodeid] = time.time()

    def pytest_runtest_logreport(self, report):
        if report.when != "call" and not (report.when == "setup" and report.skipped):
            return
        nodeid = report.nodeid
        module = nodeid.split("::")[0]
        elapsed = time.time() - self._start.get(nodeid, time.time())
        bucket = self._modules[module]
        bucket["duration"] += elapsed
        if report.passed:
            bucket["passed"] += 1
        elif report.failed:
            bucket["failed"] += 1
            self._failures.append((nodeid, str(report.longrepr).strip()))
        elif report.skipped:
            bucket["skipped"] += 1

    def pytest_terminal_summary(self, terminalreporter, exitstatus, config):
        if not _RICH or not self._modules:
            return
        console = Console()
        console.print()

        table = Table(
            title="Test Results by Module",
            box=box.ROUNDED,
            show_footer=True,
            title_style="bold cyan",
        )
        table.add_column("Module", style="cyan", no_wrap=True,
                         footer="[bold]TOTAL[/bold]")
        table.add_column("Pass",   style="green",  justify="right",
                         footer_style="bold green")
        table.add_column("Fail",   style="red",    justify="right",
                         footer_style="bold red")
        table.add_column("Skip",   style="yellow", justify="right",
                         footer_style="bold yellow")
        table.add_column("Time",   style="dim",    justify="right",
                         footer_style="bold")

        total_p = total_f = total_s = 0
        total_t = 0.0
        for module, counts in sorted(self._modules.items()):
            p, f, s, t = (counts["passed"], counts["failed"],
                          counts["skipped"], counts["duration"])
            total_p += p; total_f += f; total_s += s; total_t += t
            row_style = "on red" if f else ""
            table.add_row(
                module,
                str(p) if p else "-",
                f"[bold]{f}[/bold]" if f else "-",
                str(s) if s else "-",
                f"{t:.2f}s",
                style=row_style,
            )

        table.columns[1].footer = str(total_p) if total_p else "-"
        table.columns[2].footer = (f"[bold red]{total_f}[/bold red]"
                                   if total_f else "-")
        table.columns[3].footer = str(total_s) if total_s else "-"
        table.columns[4].footer = f"{total_t:.2f}s"

        console.print(table)

        if self._failures:
            console.print()
            fail_table = Table(
                title="Failures",
                box=box.SIMPLE_HEAVY,
                title_style="bold red",
                show_lines=True,
            )
            fail_table.add_column("Test", style="red", no_wrap=False)
            fail_table.add_column("Reason", style="white", no_wrap=False)
            for nodeid, reason in self._failures:
                short = reason.splitlines()[0][:200] if reason else "—"
                fail_table.add_row(nodeid, short)
            console.print(fail_table)


def pytest_configure(config):
    # Register the slow marker for E2E tests
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (E2E, requires infrastructure; deselect with '-m \"not slow\"')"
    )
    if _RICH:
        config.pluginmanager.register(RichReporter(), "rich_reporter")


# Test VM targeting for integration tests
import os

@pytest.fixture(scope="session")
def test_vm_host():
    """
    Returns the test VM hostname/IP for integration tests.
    Loaded from environment variable TEST_VM_HOST.
    If not set, integration tests are skipped.
    """
    return os.environ.get("TEST_VM_HOST", None)

@pytest.fixture(scope="session")
def test_vm_ssh_key():
    """
    Returns the SSH key path for test VM authentication.
    Defaults to ~/.ssh/id_ed25519 if TEST_VM_SSH_KEY not set.
    """
    return os.environ.get("TEST_VM_SSH_KEY", os.path.expanduser("~/.ssh/id_ed25519"))

def pytest_collection_modifyitems_integration(config, items):
    """
    Auto-skip integration tests if test VM is not available.
    Tests marked with @pytest.mark.integration are skipped unless
    TEST_VM_HOST environment variable is set.
    """
    if not os.environ.get("TEST_VM_HOST"):
        skip_integration = pytest.mark.skip(reason="TEST_VM_HOST not set")
        for item in items:
            if "integration" in item.keywords:
                item.add_marker(skip_integration)
