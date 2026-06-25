import pytest
from unittest.mock import patch, MagicMock

from homelab_gitops.domain.secrets_resolver import resolve_vcenter_credentials
from homelab_gitops.domain.exceptions import SecretResolutionError


def _mock_driver(values):
    """Build a fake SecretsDriver whose execute() returns mapped values by URI."""
    driver = MagicMock()

    def _execute(task):
        result = MagicMock()
        result.output = values.get(task.target, "")
        return result

    driver.execute.side_effect = _execute
    return driver


def test_resolves_from_openbao(monkeypatch):
    """Happy path: all values come from OpenBao."""
    monkeypatch.delenv("VCENTER_PASSWORD", raising=False)
    monkeypatch.delenv("VCENTER_SERVER", raising=False)
    monkeypatch.delenv("VCENTER_USER", raising=False)

    values = {
        "bao://kv/prod/platform/vcenter/VCENTER_USERNAME": "admin@vsphere",
        "bao://kv/prod/platform/vcenter/VCENTER_PASSWORD": "s3cr3t",
        "bao://kv/prod/platform/vcenter/VCENTER_SERVER": "10.0.0.9",
    }

    with patch("homelab_gitops.drivers.secrets_driver.SecretsDriver", return_value=_mock_driver(values)):
        creds = resolve_vcenter_credentials()

    assert creds["vcenter_user"] == "admin@vsphere"
    assert creds["vcenter_password"] == "s3cr3t"
    assert creds["vcenter_server"] == "10.0.0.9"


def test_falls_back_to_env(monkeypatch):
    """If OpenBao returns empty, environment variables are used."""
    monkeypatch.setenv("VCENTER_PASSWORD", "env-pass")
    monkeypatch.setenv("VCENTER_SERVER", "env-server")
    monkeypatch.setenv("VCENTER_USER", "env-user")

    # Driver returns empty for everything
    with patch("homelab_gitops.drivers.secrets_driver.SecretsDriver", return_value=_mock_driver({})):
        creds = resolve_vcenter_credentials()

    assert creds["vcenter_password"] == "env-pass"
    assert creds["vcenter_server"] == "env-server"
    assert creds["vcenter_user"] == "env-user"


def test_raises_when_password_unresolved(monkeypatch):
    """The key regression: empty bao + no env fallback must FAIL LOUDLY, not pass empty."""
    monkeypatch.delenv("VCENTER_PASSWORD", raising=False)
    monkeypatch.delenv("VCENTER_SERVER", raising=False)
    monkeypatch.delenv("VCENTER_USER", raising=False)

    with patch("homelab_gitops.drivers.secrets_driver.SecretsDriver", return_value=_mock_driver({})):
        with pytest.raises(SecretResolutionError) as exc:
            resolve_vcenter_credentials()

    msg = str(exc.value)
    # Error must be actionable
    assert "vcenter_password" in msg
    assert "VAULT_ADDR" in msg
    assert "bao" in msg


def test_raises_when_driver_construction_fails(monkeypatch):
    """If SecretsDriver cannot even be constructed and no env present, still fail loudly."""
    monkeypatch.delenv("VCENTER_PASSWORD", raising=False)

    with patch("homelab_gitops.drivers.secrets_driver.SecretsDriver", side_effect=RuntimeError("no bao")):
        with pytest.raises(SecretResolutionError):
            resolve_vcenter_credentials()


def test_server_uses_profile_fallback(monkeypatch):
    """Server can fall back to the profile host when bao + env are empty."""
    monkeypatch.setenv("VCENTER_PASSWORD", "p")
    monkeypatch.delenv("VCENTER_SERVER", raising=False)

    with patch("homelab_gitops.drivers.secrets_driver.SecretsDriver", return_value=_mock_driver({})):
        creds = resolve_vcenter_credentials(server_fallback="esxi-01.infra")

    assert creds["vcenter_server"] == "esxi-01.infra"
