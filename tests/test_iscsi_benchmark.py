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


from benchmarks.metrics_parser import MetricsParser


class TestMetricsParser:
    """Test FIO JSON metrics extraction."""

    @pytest.fixture
    def sample_fio_output(self):
        """Sample FIO JSON output."""
        return {
            "jobs": [
                {
                    "jobname": "database-70-30",
                    "read": {
                        "iops": 5000.5,
                        "bw_mean": 20000,
                        "clat_ns": {
                            "percentile": {
                                "50.000000": 1000000,
                                "95.000000": 5000000,
                                "99.000000": 10000000,
                                "100.000000": 15000000
                            }
                        }
                    },
                    "write": {
                        "iops": 2000.25,
                        "bw_mean": 8000,
                        "clat_ns": {
                            "percentile": {
                                "50.000000": 1500000,
                                "95.000000": 6000000,
                                "99.000000": 11000000,
                                "100.000000": 16000000
                            }
                        }
                    }
                }
            ]
        }

    def test_parser_init(self):
        """Test metrics parser initialization."""
        parser = MetricsParser()
        assert hasattr(parser, 'parse_fio_json')

    def test_extract_iops(self, sample_fio_output):
        """Test IOPS extraction from FIO output."""
        parser = MetricsParser()
        metrics = parser.parse_fio_json(sample_fio_output)

        assert metrics['read_iops'] == 5000.5
        assert metrics['write_iops'] == 2000.25
        assert metrics['total_iops'] == pytest.approx(7000.75)

    def test_extract_latency(self, sample_fio_output):
        """Test latency percentile extraction."""
        parser = MetricsParser()
        metrics = parser.parse_fio_json(sample_fio_output)

        assert metrics['read_lat_p50_ms'] == pytest.approx(1.0)
        assert metrics['read_lat_p95_ms'] == pytest.approx(5.0)
        assert metrics['read_lat_p99_ms'] == pytest.approx(10.0)
        assert metrics['read_lat_p100_ms'] == pytest.approx(15.0)

    def test_extract_throughput(self, sample_fio_output):
        """Test throughput extraction."""
        parser = MetricsParser()
        metrics = parser.parse_fio_json(sample_fio_output)

        assert metrics['read_throughput_mb'] == pytest.approx(20.0)
        assert metrics['write_throughput_mb'] == pytest.approx(8.0)


from benchmarks.config_capturer import ConfigCapturer


class TestConfigCapturer:
    """Test TrueNAS/ESXi configuration snapshots."""

    @pytest.fixture
    def capturer(self):
        return ConfigCapturer(truenas_host="10.10.10.20", truenas_api_key="test-key")

    def test_capturer_init(self, capturer):
        """Test config capturer initialization."""
        assert capturer.truenas_host == "10.10.10.20"
        assert capturer.truenas_api_key == "test-key"

    @patch('requests.get')
    def test_capture_truenas_pool_config(self, mock_get, capturer):
        """Test capturing TrueNAS pool configuration."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 1,
            'name': 'tank',
            'guid': '12345',
            'status': 'ONLINE'
        }
        mock_get.return_value = mock_response

        config = capturer.capture_truenas_pool()

        assert config['name'] == 'tank'
        assert config['status'] == 'ONLINE'

    @patch('requests.get')
    def test_capture_truenas_iscsi_config(self, mock_get, capturer):
        """Test capturing TrueNAS iSCSI target configuration."""
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'id': 1,
            'name': 'iSCSI_PRODUCTION',
            'comment': 'Production datastore'
        }
        mock_get.return_value = mock_response

        config = capturer.capture_iscsi_target()

        assert config['name'] == 'iSCSI_PRODUCTION'

    def test_capture_timestamp(self, capturer):
        """Test timestamp generation."""
        ts = capturer.get_timestamp()
        assert len(ts) == 19  # YYYY-MM-DD HH:MM:SS format
