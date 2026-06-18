import json
import logging
from datetime import datetime
from typing import Dict, Any
import os

logger = logging.getLogger(__name__)


class ConfigCapturer:
    """Capture TrueNAS and ESXi configuration snapshots."""

    def __init__(self, truenas_host: str, truenas_api_key: str = None, esxi_host: str = None):
        """
        Initialize config capturer.

        Args:
            truenas_host: TrueNAS API host (e.g., 10.10.10.20)
            truenas_api_key: TrueNAS API key (from environment if not provided)
            esxi_host: ESXi host IP (for ESXi configuration capture)
        """
        self.truenas_host = truenas_host
        self.truenas_api_key = truenas_api_key or os.getenv('TRUENAS_API_KEY')
        self.esxi_host = esxi_host
        self.timestamp = self.get_timestamp()

    def get_timestamp(self) -> str:
        """Get current timestamp in YYYY-MM-DD HH:MM:SS format."""
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def capture_truenas_pool(self) -> Dict[str, Any]:
        """
        Capture TrueNAS pool configuration.

        Returns:
            Dictionary with pool settings (name, status, compression, dedup, etc.)
        """
        try:
            import requests

            url = f"http://{self.truenas_host}/api/v2.0/pool"
            headers = {'Authorization': f'Bearer {self.truenas_api_key}'}

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            pool_data = response.json()
            # Handle both list and dict responses
            if isinstance(pool_data, list):
                if pool_data:
                    pool = pool_data[0]
                else:
                    return {'timestamp': self.timestamp, 'error': 'No pools found'}
            else:
                pool = pool_data

            config = {
                'timestamp': self.timestamp,
                'name': pool.get('name'),
                'guid': pool.get('guid'),
                'status': pool.get('status'),
            }
            logger.info(f"Captured TrueNAS pool: {config['name']}")
            return config
        except Exception as e:
            logger.error(f"Failed to capture TrueNAS pool config: {e}")
            return {'timestamp': self.timestamp, 'error': str(e)}

    def capture_iscsi_target(self, target_name: str = "iSCSI_PRODUCTION") -> Dict[str, Any]:
        """
        Capture TrueNAS iSCSI target configuration.

        Args:
            target_name: iSCSI target name to capture

        Returns:
            Dictionary with iSCSI target settings
        """
        try:
            import requests

            url = f"http://{self.truenas_host}/api/v2.0/iscsi/target"
            headers = {'Authorization': f'Bearer {self.truenas_api_key}'}

            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            target_data = response.json()
            # Handle both list and dict responses
            if isinstance(target_data, list):
                targets = target_data
            else:
                targets = [target_data]

            for target in targets:
                if target.get('name') == target_name:
                    config = {
                        'timestamp': self.timestamp,
                        'name': target.get('name'),
                        'id': target.get('id'),
                        'comment': target.get('comment', ''),
                    }
                    logger.info(f"Captured iSCSI target: {config['name']}")
                    return config

            logger.warning(f"iSCSI target '{target_name}' not found")
            return {'timestamp': self.timestamp, 'error': f'Target {target_name} not found'}
        except Exception as e:
            logger.error(f"Failed to capture iSCSI target config: {e}")
            return {'timestamp': self.timestamp, 'error': str(e)}

    def capture_esxi_config(self) -> Dict[str, Any]:
        """
        Capture ESXi host configuration.

        Returns:
            Dictionary with ESXi settings (HBA, multipath, queue depth)
        """
        config = {
            'timestamp': self.timestamp,
            'esxi_host': self.esxi_host,
            'note': 'Manual ESXi config capture requires govc or direct vCenter API access'
        }
        logger.info("ESXi config capture requires manual setup via govc")
        return config

    def capture_all(self) -> Dict[str, Any]:
        """
        Capture all available configurations.

        Returns:
            Dictionary with all configuration snapshots
        """
        return {
            'timestamp': self.timestamp,
            'truenas': self.capture_truenas_pool(),
            'iscsi_target': self.capture_iscsi_target(),
            'esxi': self.capture_esxi_config() if self.esxi_host else None
        }

    def save_config_snapshot(self, label: str, output_path: str = "benchmarks/configs") -> str:
        """
        Save configuration snapshot to JSON file.

        Args:
            label: Label for this snapshot (e.g., 'baseline', 'optimized-v1')
            output_path: Directory to save snapshot

        Returns:
            Path to saved snapshot file
        """
        os.makedirs(output_path, exist_ok=True)

        config = self.capture_all()
        filename = f"{output_path}/{self.timestamp.replace(' ', '-')}-{label}-config.json"

        with open(filename, 'w') as f:
            json.dump(config, f, indent=2)

        logger.info(f"Saved config snapshot to {filename}")
        return filename
