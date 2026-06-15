"""Unit tests for SecretsDriver."""

import os
import json
import pytest
import subprocess
from unittest.mock import MagicMock, patch
from homelab_gitops.drivers.secrets_driver import SecretsDriver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, NodeProfile

@pytest.fixture
def node_profile():
    return NodeProfile(
        name="test-node",
        vcenter={
            "datacenter": "dc",
            "cluster": "cl",
            "datastore": "ds",
            "network": "nw"
        },
        vm_specs={
            "cpu": 2,
            "memory": 4096,
            "disk": 40
        },
        deployment={
            "tags": ["test"],
            "roles": ["base"],
            "playbooks": ["site.yml"]
        }
    )

@pytest.fixture
def secrets_driver():
    with patch("shutil.which", return_value="/usr/bin/op"):
        with patch.dict("os.environ", {"OP_VAULT": "test-vault"}):
            return SecretsDriver()

def test_secrets_driver_init():
    with patch("shutil.which", return_value="/usr/bin/op"):
        driver = SecretsDriver(default_vault="custom-vault")
        assert driver.op_path == "/usr/bin/op"
        assert driver.default_vault == "custom-vault"

def test_secrets_driver_validate_success(secrets_driver):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert secrets_driver.validate() is True

def test_secrets_driver_validate_no_op():
    with patch("shutil.which", return_value=None):
        driver = SecretsDriver()
        assert driver.validate() is True

def test_secrets_driver_validate_failure(secrets_driver):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(PrerequisiteError, match="1Password CLI not authenticated"):
            secrets_driver.validate()

def test_secrets_driver_validate_timeout(secrets_driver):
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired(["op", "whoami"], 5)):
        with pytest.raises(PrerequisiteError, match="1Password CLI 'whoami' timed out"):
            secrets_driver.validate()

def test_secrets_driver_execute_get_env(secrets_driver, node_profile):
    with patch.dict("os.environ", {"MY_SECRET": "env-value"}):
        task = Task(type="get", target="MY_SECRET", profile=node_profile)
        result = secrets_driver.execute(task)
        assert result.success is True
        assert result.output == "env-value"

def test_secrets_driver_execute_get_op(secrets_driver, node_profile):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="op-value\n")
        task = Task(type="get", target="op://vault/item/field", profile=node_profile)
        result = secrets_driver.execute(task)
        assert result.success is True
        assert result.output == "op-value"

def test_secrets_driver_execute_get_op_constructed(secrets_driver, node_profile):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0, stdout="op-value\n")
        task = Task(type="get", target="my-item", profile=node_profile)
        result = secrets_driver.execute(task)
        assert result.success is True
        assert result.output == "op-value"
        # Check that it tried the constructed URI
        mock_run.assert_called_with(
            ["/usr/bin/op", "read", "op://test-vault/my-item/password", "-n"],
            capture_output=True, text=True, timeout=10
        )

def test_secrets_driver_execute_get_op_fallback(secrets_driver, node_profile):
    with patch("subprocess.run") as mock_run:
        # First call fails, second succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1, stderr="not found"),
            MagicMock(returncode=0, stdout="fallback-value\n")
        ]
        task = Task(type="get", target="my-item", profile=node_profile)
        result = secrets_driver.execute(task)
        assert result.success is True
        assert result.output == "fallback-value"
        assert mock_run.call_count == 2

def test_secrets_driver_execute_get_failure(secrets_driver, node_profile):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1, stderr="error")
        task = Task(type="get", target="op://vault/item/field", profile=node_profile)
        with pytest.raises(ExecutionError, match="1Password read failed"):
            secrets_driver.execute(task)

def test_secrets_driver_execute_resolve_file(secrets_driver, node_profile):
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, 
                stdout="KEY1=VAL1\nKEY2=\"VAL2\"\n# Comment\nKEY3='VAL3'\n"
            )
            task = Task(type="resolve_file", target="secrets.env", profile=node_profile)
            result = secrets_driver.execute(task)
            assert result.success is True
            output = json.loads(result.output)
            assert output["KEY1"] == "VAL1"
            assert output["KEY2"] == "VAL2"
            assert output["KEY3"] == "VAL3"

def test_secrets_driver_resolve_file_not_found(secrets_driver, node_profile):
    with patch("os.path.exists", return_value=False):
        task = Task(type="resolve_file", target="missing.env", profile=node_profile)
        with pytest.raises(ExecutionError, match="Env file not found"):
            secrets_driver.execute(task)

def test_secrets_driver_store_secret_new(secrets_driver):
    with patch("subprocess.run") as mock_run:
        # First call (get) fails, second (create) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=1),
            MagicMock(returncode=0)
        ]
        secrets_driver.store_secret("new-item", "secret-val")
        assert mock_run.call_count == 2
        mock_run.assert_called_with(
            ["/usr/bin/op", "item", "create", "--category", "login", "--title", "new-item", "password=secret-val", "--vault", "test-vault"],
            check=True, capture_output=True
        )

def test_secrets_driver_store_secret_update(secrets_driver):
    with patch("subprocess.run") as mock_run:
        # First call (get) succeeds, second (edit) succeeds
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0)
        ]
        secrets_driver.store_secret("existing-item", "new-val")
        assert mock_run.call_count == 2
        mock_run.assert_called_with(
            ["/usr/bin/op", "item", "edit", "existing-item", "password=new-val", "--vault", "test-vault"],
            check=True, capture_output=True
        )

def test_secrets_driver_store_document(secrets_driver):
    with patch("subprocess.run") as mock_run:
        # get (exists), delete, create
        mock_run.side_effect = [
            MagicMock(returncode=0),
            MagicMock(returncode=0),
            MagicMock(returncode=0)
        ]
        secrets_driver.store_document("my-doc", "/path/to/file")
        assert mock_run.call_count == 3
        mock_run.assert_called_with(
            ["/usr/bin/op", "document", "create", "/path/to/file", "--title", "my-doc", "--vault", "test-vault"],
            check=True, capture_output=True
        )

def test_secrets_driver_store_document_new(secrets_driver):
    with patch("subprocess.run") as mock_run:
        # get (not exists), create
        mock_run.side_effect = [
            MagicMock(returncode=1),
            MagicMock(returncode=0)
        ]
        secrets_driver.store_document("new-doc", "/path/to/file")
        assert mock_run.call_count == 2

def test_secrets_driver_no_op_error(secrets_driver):
    secrets_driver.op_path = None
    with pytest.raises(ExecutionError, match="'op' CLI required"):
        secrets_driver.store_secret("item", "val")
    with pytest.raises(ExecutionError, match="'op' CLI required"):
        secrets_driver.store_document("doc", "path")
    
    with patch("os.path.exists", return_value=True):
        with pytest.raises(ExecutionError, match="'op' CLI required"):
            secrets_driver._resolve_file("path")

def test_secrets_driver_get_secret_no_ref(secrets_driver):
    with pytest.raises(ExecutionError, match="No secret reference provided"):
        secrets_driver._get_secret(None)

def test_secrets_driver_get_secret_not_found_anywhere(secrets_driver):
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)
        with pytest.raises(ExecutionError, match="not found in environment or 1Password"):
            secrets_driver._get_secret("unknown-secret")

def test_secrets_driver_validate_generic_exception(secrets_driver):
    with patch("subprocess.run", side_effect=Exception("Unexpected error")):
        with pytest.raises(PrerequisiteError, match="Failed to validate 1Password CLI"):
            secrets_driver.validate()

def test_secrets_driver_execute_generic_exception(secrets_driver, node_profile):
    # Mocking _get_secret to raise a generic exception
    with patch.object(secrets_driver, "_get_secret", side_effect=ValueError("Generic error")):
        task = Task(type="get", target="MY_SECRET", profile=node_profile)
        with pytest.raises(ExecutionError, match="Secrets operation failed"):
            secrets_driver.execute(task)

def test_secrets_driver_get_secret_not_in_env_but_in_op(secrets_driver):
    # Ensure it's not in env
    with patch.dict("os.environ", {}, clear=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="op-val")
            val = secrets_driver._get_secret("my-secret")
            assert val == "op-val"

def test_secrets_driver_store_secret_failure(secrets_driver):
    with patch("subprocess.run") as mock_run:
        # get fails, create fails
        mock_run.side_effect = [
            MagicMock(returncode=1),
            subprocess.CalledProcessError(1, "op", stderr="creation failed")
        ]
        with pytest.raises(ExecutionError, match="Failed to store secret"):
            secrets_driver.store_secret("item", "val")

def test_secrets_driver_store_document_failure(secrets_driver):
    with patch("subprocess.run") as mock_run:
        # get fails, create fails
        mock_run.side_effect = [
            MagicMock(returncode=1),
            subprocess.CalledProcessError(1, "op", stderr="upload failed")
        ]
        with pytest.raises(ExecutionError, match="Failed to store document"):
            secrets_driver.store_document("doc", "path")

def test_secrets_driver_get_secret_timeout(secrets_driver):
    with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("op", 10)):
        with pytest.raises(ExecutionError, match="1Password read timed out"):
            secrets_driver._get_secret("op://vault/item/field")

def test_secrets_driver_get_secret_subprocess_error(secrets_driver):
    with patch("subprocess.run", side_effect=subprocess.SubprocessError("error")):
        with pytest.raises(ExecutionError, match="1Password execution failed"):
            secrets_driver._get_secret("op://vault/item/field")

def test_secrets_driver_resolve_file_timeout(secrets_driver):
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run", side_effect=subprocess.TimeoutExpired("op", 20)):
            with pytest.raises(ExecutionError, match="1Password inject timed out"):
                secrets_driver._resolve_file("path")

def test_secrets_driver_resolve_file_subprocess_error(secrets_driver):
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run", side_effect=subprocess.SubprocessError("error")):
            with pytest.raises(ExecutionError, match="1Password inject failed"):
                secrets_driver._resolve_file("path")

def test_secrets_driver_resolve_file_inject_failure(secrets_driver):
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1, stderr="inject failed")
            with pytest.raises(ExecutionError, match="1Password inject failed"):
                secrets_driver._resolve_file("path")

def test_secrets_driver_resolve_file_default(secrets_driver):
    with patch("os.path.exists", return_value=True):
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="K=V")
            secrets_driver._resolve_file(None)
            mock_run.assert_called_with(
                ["/usr/bin/op", "inject", "-i", "config/secrets.env"],
                capture_output=True, text=True, timeout=20
            )
