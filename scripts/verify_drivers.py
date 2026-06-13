import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add src to sys.path
sys.path.append(os.path.abspath("src"))

from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
from homelab_gitops.drivers.secrets_driver import SecretsDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError

class TestDriverValidation(unittest.TestCase):

    @patch('requests.get')
    @patch.dict(os.environ, {
        "OPNSENSE_URL": "https://opnsense.local",
        "OPNSENSE_KEY": "key",
        "OPNSENSE_SECRET": "secret"
    })
    def test_opnsense_driver_validate_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_get.return_value = mock_response
        
        driver = OPNsenseDriver()
        self.assertTrue(driver.validate())
        mock_get.assert_called_with(
            "https://opnsense.local/network/interfaces/get",
            auth=("key", "secret"),
            verify=False,
            timeout=10
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_opnsense_driver_validate_missing_env(self):
        driver = OPNsenseDriver()
        with self.assertRaises(PrerequisiteError) as cm:
            driver.validate()
        self.assertIn("OPNSENSE_URL, OPNSENSE_KEY, and OPNSENSE_SECRET must be set", str(cm.exception))

    @patch('requests.get')
    @patch.dict(os.environ, {
        "TECHNITIUM_HOST": "http://dns.local",
        "TECHNITIUM_TOKEN": "token"
    })
    def test_technitium_driver_validate_success(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_get.return_value = mock_response
        
        driver = TechnitiumDriver()
        self.assertTrue(driver.validate())
        mock_get.assert_called_with(
            "http://dns.local/api/dns/listZones",
            params={"token": "token"},
            timeout=10
        )

    @patch.dict(os.environ, {}, clear=True)
    def test_technitium_driver_validate_missing_env(self):
        driver = TechnitiumDriver()
        with self.assertRaises(PrerequisiteError) as cm:
            driver.validate()
        self.assertIn("TECHNITIUM_HOST and TECHNITIUM_TOKEN must be set", str(cm.exception))

    @patch('shutil.which')
    @patch('subprocess.run')
    def test_secrets_driver_validate_success(self, mock_run, mock_which):
        mock_which.return_value = "/usr/bin/op"
        mock_run.return_value = MagicMock(returncode=0)
        
        driver = SecretsDriver()
        self.assertTrue(driver.validate())
        mock_run.assert_called_with(
            ["/usr/bin/op", "whoami"],
            capture_output=True,
            text=True,
            timeout=5
        )

    @patch('shutil.which')
    def test_secrets_driver_validate_no_op(self, mock_which):
        mock_which.return_value = None
        driver = SecretsDriver()
        # Should return True as it falls back to ENV
        self.assertTrue(driver.validate())

if __name__ == "__main__":
    unittest.main()
