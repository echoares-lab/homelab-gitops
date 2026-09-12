"""Tests for the repo-root conftest.py suite-duration telemetry plugin.

Testing-Policy §3.1: tier durations are reported, never used to fail a build.
These run the plugin in an isolated pytester session so the assertions are
about the plugin's own output and exit status, not this suite's timing.
"""

from pathlib import Path

import pytest

pytest_plugins = ["pytester"]

_PLUGIN_SOURCE = (Path(__file__).resolve().parents[2] / "conftest.py").read_text()


@pytest.fixture
def isolated(pytester: pytest.Pytester) -> pytest.Pytester:
    pytester.makeconftest(_PLUGIN_SOURCE)
    pytester.makepyfile(test_ok="def test_ok():\n    assert True\n")
    return pytester


def test_overrun_warns_but_passes(isolated: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("GITHUB_ACTIONS", "true")
    # A target no real session can meet forces the overrun branch.
    result = isolated.runpytest_inprocess("-p", "no:cacheprovider", "--suite-seconds-target=0.000001")
    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(
        [
            "*SUITE DURATION OVER TARGET*",
            "Suite took *s, OVER the 0.00s Testing-Policy §3.1 tier target*",
            "::warning title=Suite duration over target::Suite took *",
        ]
    )


def test_overrun_has_no_annotation_outside_actions(isolated: pytest.Pytester, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    result = isolated.runpytest_inprocess("-p", "no:cacheprovider", "--suite-seconds-target=0.000001")
    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(["*SUITE DURATION OVER TARGET*"])
    assert "::warning" not in result.stdout.str()


def test_within_target_reports_telemetry(isolated: pytest.Pytester) -> None:
    result = isolated.runpytest_inprocess("-p", "no:cacheprovider", "--suite-seconds-target=600")
    assert result.ret == pytest.ExitCode.OK
    result.stdout.fnmatch_lines(
        ["*suite duration telemetry*", "Suite took *s, within the 600.00s Testing-Policy §3.1 tier target*"]
    )
    assert "OVER TARGET" not in result.stdout.str()


def test_zero_target_disables_report(isolated: pytest.Pytester) -> None:
    result = isolated.runpytest_inprocess("-p", "no:cacheprovider", "--suite-seconds-target=0")
    assert result.ret == pytest.ExitCode.OK
    assert "Suite took" not in result.stdout.str()


def test_real_failure_is_preserved(isolated: pytest.Pytester) -> None:
    isolated.makepyfile(test_bad="def test_bad():\n    assert False\n")
    result = isolated.runpytest_inprocess("-p", "no:cacheprovider", "--suite-seconds-target=0.000001")
    assert result.ret == pytest.ExitCode.TESTS_FAILED
    result.stdout.fnmatch_lines(["*SUITE DURATION OVER TARGET*"])
