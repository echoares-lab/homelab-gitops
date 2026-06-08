"""Unit tests for SecretsService."""

import pytest
import os
from unittest.mock import patch, MagicMock
from services.secrets import SecretsService

class TestSecretsServiceBootstrap:
    """Test SecretsService.bootstrap_secrets()."""

    @pytest.mark.unit
    def test_bootstrap_returns_true_when_secrets_already_loaded(self):
        """Test that bootstrap returns True if VCENTER_SERVER is already set."""
        service = SecretsService()

        with patch.dict(os.environ, {"VCENTER_SERVER": "vcenter.example.com"}):
            result = service.bootstrap_secrets()
            assert result is True

    @pytest.mark.unit
    def test_bootstrap_returns_false_when_no_token(self):
        """Test that bootstrap returns False if OP_SERVICE_ACCOUNT_TOKEN not set."""
        service = SecretsService()

        with patch.dict(os.environ, {}, clear=True):
            result = service.bootstrap_secrets()
            assert result is False

class TestSecretsServiceShouldBootstrap:
    """Test SecretsService.should_bootstrap()."""

    @pytest.mark.unit
    def test_should_bootstrap_returns_false_for_help(self):
        """Test that --help doesn't trigger bootstrap."""
        service = SecretsService()
        argv = ["manage.py", "--help"]
        assert service.should_bootstrap(argv) is False

    @pytest.mark.unit
    def test_should_bootstrap_returns_false_for_lint(self):
        """Test that lint command doesn't need secrets."""
        service = SecretsService()
        argv = ["manage.py", "lint", "ubuntu-2404-base", "01"]
        assert service.should_bootstrap(argv) is False

    @pytest.mark.unit
    def test_should_bootstrap_returns_false_for_status(self):
        """Test that status command doesn't need secrets."""
        service = SecretsService()
        argv = ["manage.py", "status"]
        assert service.should_bootstrap(argv) is False

    @pytest.mark.unit
    def test_should_bootstrap_returns_true_for_deploy(self):
        """Test that deploy command needs secrets."""
        service = SecretsService()
        argv = ["manage.py", "deploy", "ubuntu-2404-base", "01", "--host", "esxi-01"]
        assert service.should_bootstrap(argv) is True

    @pytest.mark.unit
    def test_should_bootstrap_returns_true_for_build(self):
        """Test that build command needs secrets."""
        service = SecretsService()
        argv = ["manage.py", "build", "ubuntu-2404"]
        assert service.should_bootstrap(argv) is True

    @pytest.mark.unit
    def test_should_bootstrap_returns_false_for_empty_argv(self):
        """Test that empty argv doesn't trigger bootstrap."""
        service = SecretsService()
        argv = ["manage.py"]
        assert service.should_bootstrap(argv) is False
