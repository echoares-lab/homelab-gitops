"""Unit tests for DNSService."""

import pytest
from services.dns import DNSService

class TestDNSServiceListRecords:
    """Test DNSService.list_records()."""

    @pytest.mark.unit
    def test_list_records_returns_list(self):
        """Test that list_records returns a list."""
        service = DNSService()
        result = service.list_records()

        assert isinstance(result, list)

class TestDNSServiceCreateRecord:
    """Test DNSService.create_record()."""

    @pytest.mark.unit
    def test_create_record_returns_true(self):
        """Test that create_record returns True."""
        service = DNSService()
        result = service.create_record("test.example.com", "10.10.10.50")

        assert result is True

    @pytest.mark.unit
    def test_create_record_accepts_custom_ttl(self):
        """Test that create_record accepts custom TTL."""
        service = DNSService()
        result = service.create_record("test.example.com", "10.10.10.50", ttl=7200)

        assert result is True

class TestDNSServiceDeleteRecord:
    """Test DNSService.delete_record()."""

    @pytest.mark.unit
    def test_delete_record_returns_true(self):
        """Test that delete_record returns True."""
        service = DNSService()
        result = service.delete_record("test.example.com")

        assert result is True

class TestDNSServiceValidateRecord:
    """Test DNSService.validate_record()."""

    @pytest.mark.unit
    def test_validate_record_returns_bool(self):
        """Test that validate_record returns boolean."""
        service = DNSService()
        result = service.validate_record("test.example.com", "10.10.10.50")

        assert isinstance(result, bool)
