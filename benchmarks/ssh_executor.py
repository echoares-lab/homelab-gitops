import paramiko
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)


class SSHExecutor:
    """Handle SSH connections and remote command execution."""

    def __init__(self, host: str, username: str = "ubuntu", key_path: str = None, port: int = 22, timeout: int = 30):
        """
        Initialize SSH executor.

        Args:
            host: Target host IP or hostname
            username: SSH username
            key_path: Path to SSH private key (default: ~/.ssh/id_ed25519)
            port: SSH port
            timeout: Connection timeout in seconds
        """
        self.host = host
        self.username = username
        self.port = port
        self.timeout = timeout
        self.key_path = key_path or os.path.expanduser("~/.ssh/id_ed25519")
        self.client = None

    def connect(self):
        """Establish SSH connection."""
        try:
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            self.client.connect(
                self.host,
                port=self.port,
                username=self.username,
                key_filename=self.key_path,
                timeout=self.timeout,
                look_for_keys=True,
                allow_agent=True
            )
            logger.info(f"Connected to {self.host}")
        except Exception as e:
            logger.error(f"Failed to connect to {self.host}: {e}")
            raise

    def disconnect(self):
        """Close SSH connection."""
        if self.client:
            self.client.close()
            logger.info(f"Disconnected from {self.host}")

    def execute_command(self, command: str) -> str:
        """
        Execute remote command and return output.

        Args:
            command: Command to execute

        Returns:
            Command output as string

        Raises:
            RuntimeError: If command fails
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        stdin, stdout, stderr = self.client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()

        output = stdout.read().decode('utf-8')
        error = stderr.read().decode('utf-8')

        if exit_code != 0:
            logger.error(f"Command failed on {self.host}: {error}")
            raise RuntimeError(f"Command failed: {error}")

        return output

    def transfer_file(self, local_path: str, remote_path: str):
        """
        Transfer file to remote host via SFTP.

        Args:
            local_path: Local file path
            remote_path: Remote destination path
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            sftp = self.client.open_sftp()
            sftp.put(local_path, remote_path)
            sftp.close()
            logger.info(f"Transferred {local_path} to {self.host}:{remote_path}")
        except Exception as e:
            logger.error(f"Failed to transfer file: {e}")
            raise

    def get_file(self, remote_path: str, local_path: str):
        """
        Download file from remote host.

        Args:
            remote_path: Remote file path
            local_path: Local destination path
        """
        if not self.client:
            raise RuntimeError("Not connected. Call connect() first.")

        try:
            sftp = self.client.open_sftp()
            sftp.get(remote_path, local_path)
            sftp.close()
            logger.info(f"Downloaded {remote_path} from {self.host} to {local_path}")
        except Exception as e:
            logger.error(f"Failed to download file: {e}")
            raise

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
