"""Repo-root pytest plugin: hard test-time caps (Testing-Policy §3.1).

Testing-Policy §3.1 fixes a per-tier wall-clock cap on the *whole* suite
(Tier 2 unit = 10s, Tier 3 integration = 45s, Tier 4 E2E = 60s). pytest has no
native way to fail a run for taking too long -- ``--timeout`` from
pytest-timeout is per-test, and ``--durations`` only reports. This plugin
measures the whole session and turns an over-cap run into a build failure.

The cap is supplied with ``--max-suite-seconds``; the Tier 2 value is armed by
default via ``addopts`` in pytest.ini. Tiers 3 and 4 pass their own cap on the
command line (a later CLI flag overrides addopts).

Set ``--max-suite-seconds=0`` to disable, which is only appropriate for ad-hoc
local runs -- never in CI.
"""

from __future__ import annotations

import time

import pytest

_START_KEY = pytest.StashKey[float]()
_BREACH_KEY = pytest.StashKey[str]()
_CAP_OPT = "--max-suite-seconds"


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        _CAP_OPT,
        action="store",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help=(
            "Fail the run if the entire suite takes longer than SECONDS "
            "(Testing-Policy §3.1 tier cap). 0 disables the gate."
        ),
    )


def pytest_configure(config: pytest.Config) -> None:
    # Started before collection so collection time counts toward the cap: a
    # suite that is slow to collect is still a slow suite.
    config.stash[_START_KEY] = time.monotonic()


def _elapsed(config: pytest.Config) -> float:
    return time.monotonic() - config.stash[_START_KEY]


def pytest_sessionfinish(session: pytest.Session, exitstatus: int) -> None:
    config = session.config
    cap = config.getoption(_CAP_OPT)
    if cap <= 0:
        return

    elapsed = _elapsed(config)
    if elapsed <= cap:
        return

    config.stash[_BREACH_KEY] = (
        f"Suite took {elapsed:.2f}s, over the {cap:.2f}s cap "
        f"(Testing-Policy §3.1). Refactor or parallelize the suite; "
        f"raising the cap requires a dated Policy Exception."
    )

    # Preserve a pre-existing failure status; otherwise fail the build.
    if exitstatus == 0:
        session.exitstatus = pytest.ExitCode.TESTS_FAILED


def pytest_terminal_summary(terminalreporter, exitstatus, config: pytest.Config) -> None:
    # Reported here rather than from pytest_sessionfinish so the message lands
    # inside the terminal summary that the active reporter actually renders.
    message = config.stash.get(_BREACH_KEY, None)
    if not message:
        return
    terminalreporter.write_sep("=", "SUITE DURATION GATE FAILED", red=True, bold=True)
    terminalreporter.write_line(message)
