"""Unit tests for AcmeDriver."""

import pytest
from unittest.mock import MagicMock, patch
from acme import challenges, messages
from homelab_gitops.drivers.acme_driver import AcmeDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task

@pytest.fixture
def acme_driver():
    with patch("acme.client.ClientNetwork"), \
         patch("acme.client.ClientV2.get_directory"):
        return AcmeDriver(directory_url="http://mock.directory")

def test_acme_driver_init():
    driver = AcmeDriver(directory_url="http://test.url")
    assert driver.directory_url == "http://test.url"

def test_acme_driver_validate(acme_driver):
    with patch.object(AcmeDriver, "_get_client", return_value=MagicMock()):
        assert acme_driver.validate() is True

def test_acme_driver_validate_failure(acme_driver):
    with patch.object(AcmeDriver, "_get_client", side_effect=Exception("Connection failed")):
        with pytest.raises(PrerequisiteError, match="ACME driver validation failed"):
            acme_driver.validate()

@patch("acme.messages.NewRegistration.from_data")
def test_acme_driver_register_account(mock_regr, acme_driver):
    mock_client = MagicMock()
    with patch.object(AcmeDriver, "_get_client", return_value=mock_client):
        mock_client.new_account.return_value = MagicMock()
        mock_key_wrapper = MagicMock()
        mock_key_wrapper.key.private_bytes.return_value = b"MOCK_KEY"
        acme_driver._account_key = mock_key_wrapper
        
        acme_driver.register_account("test@example.com")
        mock_client.new_account.assert_called_once()

def test_acme_driver_request_challenge(acme_driver):
    mock_client = MagicMock()
    with patch.object(AcmeDriver, "_get_client", return_value=mock_client):
        mock_order = MagicMock()
        mock_authz = MagicMock()
        mock_challb = MagicMock()
        
        # Setup challenge body
        mock_dns_chall = MagicMock(spec=challenges.DNS01)
        mock_dns_chall.token = b"raw_token"
        mock_challb.chall = mock_dns_chall
        mock_challb.response_and_validation.return_value = (None, "token123")
        
        mock_authz.body.challenges = [mock_challb]
        mock_order.authorizations = [mock_authz]
        mock_client.new_order.return_value = mock_order
        
        acme_driver._account_key = MagicMock()
        
        with patch("homelab_gitops.drivers.acme_driver.challenges.DNS01", challenges.DNS01):
            results = acme_driver.request_challenge("test.com")
            assert len(results) == 1
            assert results[0]["txt_record"] == "_acme-challenge.test.com"
            assert results[0]["validation"] == "token123"

def test_acme_driver_finalize_order(acme_driver):
    mock_client = MagicMock()
    with patch.object(AcmeDriver, "_get_client", return_value=mock_client):
        # Mock order and responses
        mock_order_ready = MagicMock()
        mock_order_ready.body.status = messages.STATUS_READY
        
        mock_order_valid = MagicMock()
        mock_order_valid.body.status = messages.STATUS_VALID
        
        mock_client.new_order.return_value = mock_order_ready
        mock_client.poll.side_effect = [mock_order_ready, mock_order_valid]
        mock_client.finalize_order.return_value = mock_order_valid
        mock_client.fetch_chain.return_value = "CERT_CHAIN"
        
        with patch("time.time", return_value=0), \
             patch("time.sleep", return_value=None), \
             patch("homelab_gitops.drivers.acme_driver.x509.load_pem_x509_csr", return_value=MagicMock()):
            cert = acme_driver.finalize_order("test.com", "CSR_PEM")
            assert cert == "CERT_CHAIN"

def test_acme_driver_execute_unsupported(acme_driver):
    task = Task(
        type="provision",
        profile=MagicMock(),
        overrides={"action": "invalid"}
    )
    with pytest.raises(ExecutionError, match="Unsupported ACME action"):
        acme_driver.execute(task)

def test_acme_driver_execute_challenge(acme_driver):
    task = Task(
        type="provision",
        profile=MagicMock(),
        overrides={"action": "challenge", "domain": "test.com"}
    )
    with patch.object(AcmeDriver, "request_challenge", return_value=[]) as mock_chall:
        acme_driver.execute(task)
        mock_chall.assert_called_once_with("test.com")

def test_acme_driver_execute_finalize(acme_driver):
    task = Task(
        type="provision",
        profile=MagicMock(),
        overrides={"action": "finalize", "domain": "test.com", "csr": "CSR"}
    )
    with patch.object(AcmeDriver, "finalize_order", return_value="CERT") as mock_fin:
        result = acme_driver.execute(task)
        assert result.success is True
        assert result.output == {"certificate": "CERT"}
        mock_fin.assert_called_once_with("test.com", "CSR")
