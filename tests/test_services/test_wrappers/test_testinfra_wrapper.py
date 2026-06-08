import pytest
from unittest.mock import Mock, patch, MagicMock
from services.wrappers.testinfra_wrapper import TestinfraWrapper


class TestTestinfraWrapperInit:
    @patch("shutil.which")
    def test_init_validates_pytest(self, mock_which):
        mock_which.return_value = "/usr/bin/pytest"
        wrapper = TestinfraWrapper()
        mock_which.assert_called_with("pytest")


class TestTestinfraWrapperRunTests:
    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_tests_executes_pytest(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/pytest"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = TestinfraWrapper()
        result = wrapper.run_tests(hosts=["ansible@10.10.10.50"])

        assert result is True
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "pytest"
        assert "--hosts=ansible@10.10.10.50" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_tests_with_multiple_hosts(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/pytest"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = TestinfraWrapper()
        wrapper.run_tests(hosts=["ansible@10.10.10.50", "ansible@10.10.10.51"])

        args, _ = mock_run.call_args
        cmd = args[0]
        assert "--hosts=ansible@10.10.10.50 ansible@10.10.10.51" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_tests_with_ssh_key(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/pytest"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = TestinfraWrapper()
        wrapper.run_tests(hosts=["ansible@10.10.10.50"], ssh_key="/home/user/.ssh/id_ed25519")

        args, _ = mock_run.call_args
        cmd = args[0]
        assert "--ssh-extra-args=" in " ".join(cmd)
        assert "IdentityFile=/home/user/.ssh/id_ed25519" in " ".join(cmd)

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_tests_without_sudo(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/pytest"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = TestinfraWrapper()
        wrapper.run_tests(hosts=["ansible@10.10.10.50"], sudo=False)

        args, _ = mock_run.call_args
        cmd = args[0]
        assert "--sudo" not in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_tests_returns_false_on_failure(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/pytest"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        wrapper = TestinfraWrapper()
        result = wrapper.run_tests(hosts=["ansible@10.10.10.50"])

        assert result is False
