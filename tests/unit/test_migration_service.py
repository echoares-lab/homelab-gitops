"""Unit tests for MigrationService."""

import pytest
from unittest.mock import MagicMock, patch
from homelab_gitops.domain.migration import MigrationService

@pytest.fixture
def mock_driver():
    return MagicMock()

@pytest.fixture
def migration_service(mock_driver):
    return MigrationService(
        opnsense_driver=mock_driver,
        technitium_driver=mock_driver,
        migration_driver=mock_driver
    )

def test_migration_service_discover(migration_service, mock_driver):
    mock_driver.execute.return_value = MagicMock(success=True, output={"interfaces": [], "scopes": []})
    results = migration_service.discover()
    assert results is not None

def test_migration_service_migrate_dhcp(migration_service, mock_driver):
    discovery_data = {
        'opnsense_interfaces': [{'interface': 'S', 'descr': 'Source'}],
        'technitium_scopes': [{'name': 'T'}]
    }
    with patch.object(migration_service, "discover", return_value=discovery_data):
        mock_driver.execute.return_value = MagicMock(success=True)
        results = migration_service.migrate_dhcp(source="S", target="T")
        assert results is not None

def test_migration_service_rollback(migration_service, mock_driver):
    mock_driver.execute.return_value = MagicMock(success=True)
    results = migration_service.rollback()
    assert results is not None
