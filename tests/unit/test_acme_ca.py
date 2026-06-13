"""Unit tests for ACME Certificate Service."""

import pytest
from unittest.mock import MagicMock, patch
from homelab_gitops.domain.certificate import CertificateService
from homelab_gitops.domain.models import Task

@pytest.fixture
def mock_drivers():
    """Mock drivers for the CertificateService."""
    acme_driver = MagicMock()
    dns_driver = MagicMock()
    secrets_driver = MagicMock()
    return acme_driver, dns_driver, secrets_driver

def test_certificate_service_init(mock_drivers):
    """Test CertificateService initialization."""
    acme, dns, secrets = mock_drivers
    service = CertificateService(acme, dns, secrets)
    assert service.acme == acme
    assert service.dns == dns
    assert service.secrets == secrets

@patch("time.sleep", return_value=None)
@patch("cryptography.hazmat.primitives.asymmetric.rsa.generate_private_key")
@patch("cryptography.x509.CertificateSigningRequestBuilder")
def test_issue_certificate_workflow(mock_csr_builder, mock_gen_key, mock_sleep, mock_drivers):
    """Test the full certificate issuance workflow."""
    acme, dns, secrets = mock_drivers
    service = CertificateService(acme, dns, secrets)

    # 1. Setup mocks
    domain = "test.mgmt.plexplease.com"
    email = "admin@test.com"
    
    # Mock private key
    mock_key = MagicMock()
    mock_key.private_bytes.return_value = b"MOCK_KEY_PEM"
    mock_gen_key.return_value = mock_key

    # Mock ACME challenge
    acme.request_challenge.return_value = [{
        "txt_record": "_acme-challenge.test.mgmt.plexplease.com",
        "validation": "MOCK_TOKEN"
    }]
    
    # Mock ACME finalization
    acme.finalize_order.return_value = "MOCK_CERT_PEM"

    # Mock CSR
    mock_csr = MagicMock()
    mock_csr.public_bytes.return_value = b"MOCK_CSR_PEM"
    mock_csr_builder.return_value.subject_name.return_value.add_extension.return_value.sign.return_value = mock_csr

    # 2. Execute service call
    cert = service.issue_certificate(domain, email)

    # 3. Assertions
    assert cert == "MOCK_CERT_PEM"
    
    # Verify account registration
    acme.register_account.assert_called_once_with(email)
    
    # Verify DNS record creation
    dns.execute.assert_any_call(pytest.approx_task(Task(
        type="provision",
        profile=service._dns_profile,
        overrides={
            "resource": "record",
            "action": "create",
            "zone": "plexplease.com",
            "domain": "_acme-challenge.test.mgmt.plexplease.com",
            "type": "TXT",
            "text": "MOCK_TOKEN",
            "ttl": 60
        }
    )))
    
    # Verify 1Password storage
    secrets.store_secret.assert_any_call(f"cert-{domain}-key", "MOCK_KEY_PEM")
    secrets.store_secret.assert_any_call(f"cert-{domain}-chain", "MOCK_CERT_PEM")
    
    # Verify DNS cleanup
    dns.execute.assert_any_call(pytest.approx_task(Task(
        type="destroy",
        profile=service._dns_profile,
        overrides={
            "resource": "record",
            "action": "delete",
            "zone": "plexplease.com",
            "domain": "_acme-challenge.test.mgmt.plexplease.com",
            "type": "TXT",
            "text": "MOCK_TOKEN"
        }
    )))

def test_issue_certificate_cleanup_on_failure(mock_drivers):
    """Test that DNS cleanup is performed even if ACME finalization fails."""
    acme, dns, secrets = mock_drivers
    service = CertificateService(acme, dns, secrets)

    domain = "fail.mgmt.plexplease.com"
    email = "admin@fail.com"
    
    acme.request_challenge.return_value = [{
        "txt_record": "_acme-challenge.fail.mgmt.plexplease.com",
        "validation": "FAIL_TOKEN"
    }]
    
    # Fail during finalization
    acme.finalize_order.side_effect = Exception("Finalization failed")

    with patch("time.sleep", return_value=None):
        with pytest.raises(Exception, match="Finalization failed"):
            service.issue_certificate(domain, email)

    # Verify DNS cleanup was still called
    dns.execute.assert_any_call(pytest.approx_task(Task(
        type="destroy",
        profile=service._dns_profile,
        overrides={
            "resource": "record",
            "action": "delete",
            "zone": "plexplease.com",
            "domain": "_acme-challenge.fail.mgmt.plexplease.com",
            "type": "TXT",
            "text": "FAIL_TOKEN"
        }
    )))

# Helper for comparing Tasks in mock calls
def approx_task(expected_task):
    class TaskMatcher:
        def __init__(self, expected):
            self.expected = expected
        def __eq__(self, actual):
            return (actual.type == self.expected.type and 
                    actual.target == self.expected.target and 
                    actual.overrides == self.expected.overrides)
        def __repr__(self):
            return repr(self.expected)
    return TaskMatcher(expected_task)

pytest.approx_task = approx_task
