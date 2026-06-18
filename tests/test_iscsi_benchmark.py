import pytest
import json
from unittest.mock import Mock, patch, MagicMock
from benchmarks.ssh_executor import SSHExecutor


class TestSSHExecutor:
    """Test SSH connection and FIO execution."""

    @pytest.fixture
    def executor(self):
        return SSHExecutor(host="10.10.10.50", username="ubuntu", key_path="/home/ubuntu/.ssh/id_ed25519")

    def test_executor_init(self, executor):
        """Test SSH executor initialization."""
        assert executor.host == "10.10.10.50"
        assert executor.username == "ubuntu"
        assert executor.key_path == "/home/ubuntu/.ssh/id_ed25519"

    @patch('paramiko.SSHClient')
    def test_execute_command_success(self, mock_ssh_client, executor):
        """Test successful command execution."""
        mock_client = MagicMock()
        mock_ssh_client.return_value = mock_client
        mock_stdin, mock_stdout, mock_stderr = MagicMock(), MagicMock(), MagicMock()
        mock_stdout.read.return_value = b"output"
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stderr.read.return_value = b""
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        executor.client = mock_client
        result = executor.execute_command("ls -la")

        assert result == "output"
        mock_client.exec_command.assert_called_once_with("ls -la")

    @patch('paramiko.SSHClient')
    def test_execute_command_with_error(self, mock_ssh_client, executor):
        """Test command execution with error."""
        mock_client = MagicMock()
        mock_ssh_client.return_value = mock_client
        mock_stdin, mock_stdout, mock_stderr = MagicMock(), MagicMock(), MagicMock()
        mock_stdout.read.return_value = b""
        mock_stdout.channel.recv_exit_status.return_value = 1
        mock_stderr.read.return_value = b"error message"
        mock_client.exec_command.return_value = (mock_stdin, mock_stdout, mock_stderr)

        executor.client = mock_client
        with pytest.raises(RuntimeError, match="error message"):
            executor.execute_command("bad_command")

    def test_transfer_file(self, executor):
        """Test file transfer setup (mocked)."""
        # Mock will be implemented in SSH executor
        assert hasattr(executor, 'transfer_file')
