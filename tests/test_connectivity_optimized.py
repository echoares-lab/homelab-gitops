import unittest
from unittest.mock import patch, MagicMock
import sys
import os

# Ensure scripts directory is in path
sys.path.append(os.path.join(os.path.dirname(__file__), '..', 'scripts'))
from test_connectivity import check_ssh

class TestConnectivity(unittest.TestCase):
    @patch('socket.create_connection')
    @patch('time.sleep')
    @patch('builtins.print')
    def test_check_ssh_success_immediate(self, mock_print, mock_sleep, mock_connect):
        # Mock successful connection
        mock_connect.return_value = MagicMock()

        result = check_ssh("127.0.0.1", timeout=10)

        self.assertTrue(result)
        self.assertEqual(mock_connect.call_count, 1)
        self.assertEqual(mock_sleep.call_count, 0)

    @patch('socket.create_connection')
    @patch('time.sleep')
    @patch('builtins.print')
    def test_check_ssh_success_after_retries(self, mock_print, mock_sleep, mock_connect):
        # Mock connection failure then success
        mock_connect.side_effect = [ConnectionRefusedError, ConnectionRefusedError, MagicMock()]

        result = check_ssh("127.0.0.1", timeout=60)

        self.assertTrue(result)
        self.assertEqual(mock_connect.call_count, 3)
        self.assertEqual(mock_sleep.call_count, 2)

        # Check backoff: first sleep 1s, second sleep 2s
        mock_sleep.assert_any_call(1)
        mock_sleep.assert_any_call(2)

    @patch('socket.create_connection')
    @patch('time.sleep')
    @patch('builtins.print')
    def test_check_ssh_timeout(self, mock_print, mock_sleep, mock_connect):
        # Mock persistent failure
        mock_connect.side_effect = ConnectionRefusedError

        # We need to control time.time() to simulate timeout without actually waiting
        with patch('time.time') as mock_time:
            # Start at 0, then increment by 5 on each check + some for sleep
            mock_time.side_effect = [0, 0, 1, 1, 3, 3, 7, 7, 15, 15, 25, 25, 35]

            result = check_ssh("127.0.0.1", timeout=10)

        self.assertFalse(result)
        # Should have tried a few times
        self.assertGreater(mock_connect.call_count, 1)

if __name__ == '__main__':
    unittest.main()
