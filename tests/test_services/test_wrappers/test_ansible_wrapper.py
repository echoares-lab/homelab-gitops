import pytest
from unittest.mock import Mock, patch, MagicMock
from services.wrappers.ansible_wrapper import AnsibleWrapper


class TestAnsibleWrapperInit:
    @patch("shutil.which")
    def test_init_validates_ansible_playbook(self, mock_which):
        mock_which.return_value = "/usr/bin/ansible-playbook"
        wrapper = AnsibleWrapper()
        mock_which.assert_called_with("ansible-playbook")


class TestAnsibleWrapperRunPlaybook:
    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_playbook_executes_playbook(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/ansible-playbook"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = AnsibleWrapper()
        result = wrapper.run_playbook("ansible/site.yml")

        assert result is True
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "ansible-playbook"
        assert "ansible/site.yml" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_playbook_with_extra_vars(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/ansible-playbook"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = AnsibleWrapper()
        wrapper.run_playbook(
            "ansible/site.yml",
            extra_vars={"env": "prod", "debug": "false"}
        )

        args, _ = mock_run.call_args
        cmd = args[0]
        assert "-e" in cmd
        assert "env=prod" in cmd
        assert "debug=false" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_playbook_with_tags(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/ansible-playbook"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = AnsibleWrapper()
        wrapper.run_playbook("ansible/site.yml", tags=["docker", "security"])

        args, _ = mock_run.call_args
        cmd = args[0]
        assert "-t" in cmd
        assert "docker,security" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_run_playbook_returns_false_on_failure(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/ansible-playbook"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        wrapper = AnsibleWrapper()
        result = wrapper.run_playbook("ansible/site.yml")

        assert result is False


class TestAnsibleWrapperValidateSyntax:
    @patch("subprocess.run")
    @patch("shutil.which")
    def test_validate_syntax_checks_playbook(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/ansible-playbook"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = AnsibleWrapper()
        result = wrapper.validate_syntax("ansible/site.yml")

        assert result is True
        args, _ = mock_run.call_args
        cmd = args[0]
        assert "--syntax-check" in cmd
