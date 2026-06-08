import pytest
from unittest.mock import patch, MagicMock
from services.wrappers.base_wrapper import BaseWrapper


class ConcreteWrapper(BaseWrapper):
    """Concrete implementation for testing."""

    @property
    def tool_name(self) -> str:
        return "test-tool"


class TestBaseWrapperInit:
    """Test BaseWrapper initialization and tool validation."""

    @patch("shutil.which")
    def test_init_validates_tool_exists(self, mock_which):
        """BaseWrapper should validate tool is in PATH."""
        mock_which.return_value = "/usr/bin/test-tool"
        wrapper = ConcreteWrapper()
        mock_which.assert_called_once_with("test-tool")

    @patch("shutil.which")
    def test_init_raises_if_tool_not_found(self, mock_which):
        """BaseWrapper should raise RuntimeError if tool not found."""
        mock_which.return_value = None
        with pytest.raises(RuntimeError, match="test-tool not found in PATH"):
            ConcreteWrapper()


class TestBaseWrapperRunCommand:
    """Test BaseWrapper._run_command method."""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_run_command_executes_command(self, mock_run, mock_which):
        """_run_command should execute subprocess.run with correct args."""
        mock_which.return_value = "/usr/bin/test-tool"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "output"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        wrapper = ConcreteWrapper()
        result = wrapper._run_command(["echo", "hello"])

        assert result == mock_result
        mock_run.assert_called_once()
        args, kwargs = mock_run.call_args
        assert args[0] == ["echo", "hello"]
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_run_command_raises_on_exception(self, mock_run, mock_which):
        """_run_command should raise RuntimeError on subprocess failure."""
        mock_which.return_value = "/usr/bin/test-tool"
        mock_run.side_effect = Exception("Command failed")

        wrapper = ConcreteWrapper()
        with pytest.raises(RuntimeError, match="Failed to execute test-tool"):
            wrapper._run_command(["test"])
