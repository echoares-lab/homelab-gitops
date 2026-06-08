import pytest
from unittest.mock import Mock, patch, MagicMock
from services.wrappers.tofu_wrapper import TofuWrapper


class TestTofuWrapperInit:
    """Test TofuWrapper initialization."""

    @patch("shutil.which")
    def test_init_with_defaults(self, mock_which):
        """TofuWrapper should initialize with default workspace and chdir."""
        mock_which.return_value = "/usr/bin/tofu"
        wrapper = TofuWrapper()
        assert wrapper.workspace == "default"
        assert wrapper.chdir == "tofu/"

    @patch("shutil.which")
    def test_init_with_custom_workspace(self, mock_which):
        """TofuWrapper should accept custom workspace."""
        mock_which.return_value = "/usr/bin/tofu"
        wrapper = TofuWrapper(workspace="prod")
        assert wrapper.workspace == "prod"


class TestTofuWrapperApply:
    """Test TofuWrapper.apply method."""

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_apply_builds_correct_command(self, mock_which, mock_run):
        """apply() should build tofu apply command."""
        mock_which.return_value = "/usr/bin/tofu"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = TofuWrapper(workspace="test")
        result = wrapper.apply()

        assert result is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "tofu"
        assert "-chdir=tofu/" in cmd
        assert "apply" in cmd
        assert "-auto-approve" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_apply_returns_false_on_failure(self, mock_which, mock_run):
        """apply() should return False if command fails."""
        mock_which.return_value = "/usr/bin/tofu"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        wrapper = TofuWrapper()
        result = wrapper.apply()

        assert result is False


class TestTofuWrapperDestroy:
    """Test TofuWrapper.destroy method."""

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_destroy_builds_correct_command(self, mock_which, mock_run):
        """destroy() should build tofu destroy command."""
        mock_which.return_value = "/usr/bin/tofu"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = TofuWrapper()
        result = wrapper.destroy()

        assert result is True
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        cmd = args[0]
        assert "destroy" in cmd
        assert "-auto-approve" in cmd


class TestTofuWrapperWorkspace:
    """Test TofuWrapper workspace management."""

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_workspace_new_creates_workspace(self, mock_which, mock_run):
        """workspace_new() should create new OpenTofu workspace."""
        mock_which.return_value = "/usr/bin/tofu"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = TofuWrapper()
        result = wrapper.workspace_new("ubuntu-2404-01")

        assert result is True
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        cmd = args[0]
        assert "workspace" in cmd
        assert "new" in cmd
        assert "ubuntu-2404-01" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_workspace_delete_removes_workspace(self, mock_which, mock_run):
        """workspace_delete() should delete OpenTofu workspace."""
        mock_which.return_value = "/usr/bin/tofu"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = TofuWrapper()
        result = wrapper.workspace_delete("ubuntu-2404-01")

        assert result is True
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        cmd = args[0]
        assert "workspace" in cmd
        assert "delete" in cmd
        assert "-force" in cmd
