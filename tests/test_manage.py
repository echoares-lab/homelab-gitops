import pytest
import sys
from unittest.mock import patch
import manage

def test_load_vault_subprocess_error():
    with patch("manage.os.path.exists", return_value=True):
        with patch("manage.subprocess.run") as mock_run:
            mock_run.side_effect = Exception("Mocked error")
            with patch("manage.console.print") as mock_print:
                with patch("manage.sys.exit") as mock_exit:
                    manage.load_vault()

                    # Check that console.print was called with the error
                    mock_print.assert_called_once_with("[red]Error: Mocked error[/red]")

                    # Check that sys.exit was called with exit code 1
                    mock_exit.assert_called_once_with(1)
