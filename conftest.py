"""Repo-root pytest plugin: suite-duration telemetry (Testing-Policy §3.1).

Testing-Policy §3.1 (updated 2026-09-04) sets a per-tier wall-clock *target*
for the whole suite (Tier 2 unit ~10s, Tier 3 integration ~45s, Tier 4 E2E
~60s) and says the numbers are "telemetry reported ... without failing builds
solely on duration". pytest has no native whole-session timer -- ``--timeout``
from pytest-timeout is per-test and ``--durations`` only ranks tests -- so this
plugin measures the session (collection included) and reports it against the
tier target.

An overrun never changes the exit status. It is made loud instead: a red
banner in the terminal summary and, under GitHub Actions, a ``::warning::``
workflow annotation so the regression is visible on the run without turning a
slow runner into a red build. The 2026-09-11 incident that motivated this:
the same commit measured 7.2s on an idle ARC runner and 24.7s when eight jobs
landed on the node at once (echoares-lab/homelab-gitops actions/runs/34658572448),
so a hard cap on wall-clock was gating runner contention, not the suite.

The target is supplied with ``--suite-seconds-target``; the Tier 2 value is
armed by default via ``addopts`` in pytest.ini. Tiers 3 and 4 pass their own
target on the command line (a later CLI flag overrides addopts). ``0`` turns
the report off.
"""

from __future__ import annotations

import os
import time

import pytest

_START_KEY = pytest.StashKey[float]()
_REPORT_KEY = pytest.StashKey[str]()
_OVERRUN_KEY = pytest.StashKey[bool]()
_TARGET_OPT = "--suite-seconds-target"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        _TARGET_OPT,
        action="store",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help=(
            "Report the whole-suite wall-clock time against this Testing-Policy "
            "§3.1 tier target. Overruns warn; they never fail the run. 0 disables "
            "the report."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    # Started before collection so collection time counts toward the figure: a
    # suite that is slow to collect is still a slow suite.
    config.stash[_START_KEY] = time.monotonic()


def _elapsed(config: pytest.Config) -> float:
    return time.monotonic() - config.stash[_START_KEY]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    target = config.getoption(_TARGET_OPT)
    if target <= 0:
        return

    elapsed = _elapsed(config)
    over = elapsed > target
    config.stash[_OVERRUN_KEY] = over
    verdict = "OVER" if over else "within"
    config.stash[_REPORT_KEY] = (
        f"Suite took {elapsed:.2f}s, {verdict} the {target:.2f}s Testing-Policy "
        f"§3.1 tier target (telemetry only; the exit status is unaffected)."
    )
    # Deliberately no change to session.exitstatus: §3.1 forbids failing a
    # build solely on duration.


def pytest_terminal_summary(terminalreporter, exitstatus, config: pytest.Config) -> None:
    # Reported here rather than from pytest_sessionfinish so the message lands
    # inside the terminal summary that the active reporter actually renders.
    message = config.stash.get(_REPORT_KEY, None)
    if not message:
        return
    if config.stash.get(_OVERRUN_KEY, False):
        terminalreporter.write_sep("=", "SUITE DURATION OVER TARGET", red=True, bold=True)
        terminalreporter.write_line(message)
        if os.environ.get("GITHUB_ACTIONS") == "true":
            # Workflow-command annotation: shows on the run summary and the PR
            # checks tab without failing the job.
            terminalreporter.write_line(f"::warning title=Suite duration over target::{message}")
    else:
        terminalreporter.write_sep("=", "suite duration telemetry")
        terminalreporter.write_line(message)
