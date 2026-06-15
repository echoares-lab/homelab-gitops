"""Unit tests for BackupService."""

import pytest
from unittest.mock import MagicMock, ANY
from homelab_gitops.domain.backup import BackupService
from homelab_gitops.domain.models import TaskResult

@pytest.fixture
def mock_opnsense():
    return MagicMock()

@pytest.fixture
def mock_technitium():
    return MagicMock()

@pytest.fixture
def mock_secrets():
    return MagicMock()

@pytest.fixture
def backup_service(mock_opnsense, mock_technitium, mock_secrets):
    return BackupService(
        opnsense_driver=mock_opnsense,
        technitium_driver=mock_technitium,
        secrets_driver=mock_secrets
    )

def test_run_backup_success(backup_service, mock_opnsense, mock_technitium, mock_secrets):
    # Setup mocks
    mock_opnsense.execute.return_value = TaskResult(
        success=True,
        task_type="backup",
        output={"content": "<config>opnsense</config>"},
        duration=1.0
    )
    mock_technitium.execute.return_value = TaskResult(
        success=True,
        task_type="backup",
        output={"zones": [{"name": "example.com"}]},
        duration=1.0
    )

    # Run backup
    results = backup_service.run_backup()

    # Verify results
    assert len(results) == 2
    assert results[0]["service"] == "OPNsense"
    assert results[0]["status"] == "success"
    assert results[1]["service"] == "Technitium"
    assert results[1]["status"] == "success"

    # Verify OPNsense driver call
    mock_opnsense.execute.assert_called_once()
    task = mock_opnsense.execute.call_args[0][0]
    assert task.type == "backup"
    assert task.overrides["resource"] == "backup"
    assert task.overrides["action"] == "export"

    # Verify Technitium driver call
    mock_technitium.execute.assert_called_once()
    task = mock_technitium.execute.call_args[0][0]
    assert task.type == "backup"
    assert task.overrides["resource"] == "backup"
    assert task.overrides["action"] == "export"

    # Verify Secrets driver calls
    assert mock_secrets.store_document.call_count == 2
    
    # Check calls
    calls = mock_secrets.store_document.call_args_list
    
    # Verify OPNsense backup storage
    opnsense_call = next(c for c in calls if "opnsense-config-" in c.kwargs['title'])
    assert opnsense_call.kwargs['file_path'] is not None
    
    # Verify Technitium backup storage
    technitium_call = next(c for c in calls if "technitium-zones-" in c.kwargs['title'])
    assert technitium_call.kwargs['file_path'] is not None

def test_run_backup_opnsense_failure(backup_service, mock_opnsense, mock_technitium, mock_secrets):
    # Setup mocks: OPNsense fails, Technitium succeeds
    mock_opnsense.execute.return_value = TaskResult(
        success=False,
        task_type="backup",
        output={},
        duration=1.0,
        error="Connection timeout"
    )
    mock_technitium.execute.return_value = TaskResult(
        success=True,
        task_type="backup",
        output={"zones": []},
        duration=1.0
    )

    # Run backup
    results = backup_service.run_backup()

    # Verify results
    assert results[0]["service"] == "OPNsense"
    assert results[0]["status"] == "failed"
    assert results[0]["error"] == "Connection timeout"
    
    assert results[1]["service"] == "Technitium"
    assert results[1]["status"] == "success"

    # Verify Secrets driver called only once (for Technitium)
    mock_secrets.store_document.assert_called_once()

def test_run_backup_exception(backup_service, mock_opnsense, mock_technitium, mock_secrets):
    # Setup mocks: OPNsense raises exception
    mock_opnsense.execute.side_effect = Exception("Unexpected error")
    mock_technitium.execute.return_value = TaskResult(
        success=True,
        task_type="backup",
        output={"zones": []},
        duration=1.0
    )

    # Run backup
    results = backup_service.run_backup()

    # Verify results
    assert results[0]["service"] == "OPNsense"
    assert results[0]["status"] == "failed"
    assert results[0]["error"] == "Unexpected error"

    assert results[1]["service"] == "Technitium"
    assert results[1]["status"] == "success"
