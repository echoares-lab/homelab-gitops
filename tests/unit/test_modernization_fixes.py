import pytest
import os
import ipaddress
from unittest.mock import MagicMock, patch
from homelab_gitops.domain.dns import DNSService
from homelab_gitops.drivers.opnsense_driver import OPNsenseDriver
from homelab_gitops.drivers.secrets_driver import SecretsDriver
from homelab_gitops.cli.plugin_loader import PluginLoader
from homelab_gitops.domain.models import Task, TaskResult
from homelab_gitops.drivers.technitium_driver import TechnitiumDriver

def test_dns_service_calculate_ptr():
    service = DNSService(driver=MagicMock())
    
    # IPv4
    zone, domain = service._calculate_ptr("192.168.1.10")
    assert domain == "10.1.168.192.in-addr.arpa"
    assert zone == "1.168.192.in-addr.arpa"
    
    # IPv4 with CIDR
    zone, domain = service._calculate_ptr("192.168.1.10/24")
    assert domain == "10.1.168.192.in-addr.arpa"
    assert zone == "1.168.192.in-addr.arpa"
    
    zone, domain = service._calculate_ptr("10.0.0.5/8")
    assert domain == "5.0.0.10.in-addr.arpa"
    assert zone == "10.in-addr.arpa"
    
    # IPv6
    ipv6_addr = "2001:db8::1"
    zone, domain = service._calculate_ptr(ipv6_addr)
    assert domain.endswith(".ip6.arpa")
    assert zone.endswith(".ip6.arpa")
    
    # IPv6 with CIDR
    zone, domain = service._calculate_ptr("2001:db8::1/32")
    assert domain.endswith(".ip6.arpa")
    # 2001:0db8 -> 8.b.d.0.1.0.0.2.ip6.arpa
    assert zone == "8.b.d.0.1.0.0.2.ip6.arpa"

    # Invalid IP
    with pytest.raises(ValueError, match="Invalid IP address for PTR calculation"):
        service._calculate_ptr("invalid-ip")

def test_opnsense_driver_ssl_verify_default():
    with patch.dict(os.environ, {}, clear=True):
        driver = OPNsenseDriver()
        assert driver.verify is True
        
    with patch.dict(os.environ, {"OPNSENSE_VERIFY": "false"}):
        driver = OPNsenseDriver()
        assert driver.verify is False
        
    with patch.dict(os.environ, {"OPNSENSE_VERIFY": "true"}):
        driver = OPNsenseDriver()
        assert driver.verify is True

def test_secrets_driver_field_overrides():
    with patch("shutil.which", return_value="/usr/bin/op"):
        driver = SecretsDriver()
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="secret_val")
            
            # Test default field (password)
            val = driver._get_secret("my-item")
            assert val == "secret_val"
            # Check if any call matches what we expect
            mock_run.assert_any_call(
                ["/usr/bin/op", "read", "op://homelab-gitops/my-item/password", "-n"],
                capture_output=True, text=True, timeout=10
            )
            
            # Test explicit field override
            val = driver._get_secret("my-item", overrides={"field": "api-key"})
            assert val == "secret_val"
            mock_run.assert_any_call(
                ["/usr/bin/op", "read", "op://homelab-gitops/my-item/api-key", "-n"],
                capture_output=True, text=True, timeout=10
            )

def test_plugin_loader_syntax_error(tmp_path):
    # Create a dummy package structure
    pkg_dir = tmp_path / "fake_plugins"
    pkg_dir.mkdir()
    (pkg_dir / "__init__.py").touch()
    (pkg_dir / "bad_plugin.py").write_text("this is a syntax error")
    
    loader = PluginLoader("fake_plugins")
    
    with patch("importlib.import_module") as mock_import:
        # Mock the package import
        mock_package = MagicMock()
        mock_package.__file__ = str(pkg_dir / "__init__.py")
        
        def side_effect(name):
            if name == "fake_plugins":
                return mock_package
            if name == "fake_plugins.bad_plugin":
                raise SyntaxError("Invalid syntax")
            return MagicMock()
            
        mock_import.side_effect = side_effect
        
        with pytest.raises(SyntaxError):
            loader.load_plugins()

def test_dns_service_provision_manual():
    mock_driver = MagicMock()
    service = DNSService(driver=mock_driver)
    
    # Mock successful A record creation
    mock_driver.execute.return_value = TaskResult(success=True, task_type="provision", output={}, duration=0.1)
    
    results = service.provision_manual("test-node", "192.168.1.10")
    
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is True
    assert mock_driver.execute.call_count == 2

def test_dns_service_deprovision_manual():
    mock_driver = MagicMock()
    service = DNSService(driver=mock_driver)
    
    mock_driver.execute.return_value = TaskResult(success=True, task_type="destroy", output={}, duration=0.1)
    
    results = service.deprovision_manual("test-node", "192.168.1.10")
    
    assert len(results) == 2
    assert results[0].success is True
    assert results[1].success is True
    assert mock_driver.execute.call_count == 2

def test_opnsense_driver_validate():
    driver = OPNsenseDriver()
    driver.url = "https://opnsense.local"
    driver.key = "key"
    driver.secret = "secret"
    
    with patch("requests.get") as mock_get:
        mock_get.return_value = MagicMock(status_code=200)
        assert driver.validate() is True
        
        mock_get.return_value = MagicMock(status_code=401)
        from homelab_gitops.drivers.exceptions import PrerequisiteError
        with pytest.raises(PrerequisiteError, match="Invalid OPNsense API credentials"):
            driver.validate()

def test_opnsense_driver_execute_vlan():
    driver = OPNsenseDriver()
    driver.url = "https://opnsense.local"
    driver.key = "key"
    driver.secret = "secret"
    
    task = Task(
        type="provision",
        profile=MagicMock(),
        overrides={
            "resource": "vlan",
            "action": "create",
            "interface": "lan",
            "vlan_id": 100,
            "description": "Test VLAN"
        }
    )
    
    with patch("requests.post") as mock_post:
        mock_post.return_value = MagicMock(status_code=200)
        mock_post.return_value.json.return_value = {"status": "ok"}
        
        result = driver.execute(task)
        assert result.success is True
        assert result.output == {"status": "ok"}

def test_secrets_driver_validate():
    with patch("shutil.which", return_value="/usr/bin/op"):
        driver = SecretsDriver()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert driver.validate() is True
            
            mock_run.return_value = MagicMock(returncode=1)
            from homelab_gitops.drivers.exceptions import PrerequisiteError
            with pytest.raises(PrerequisiteError, match="1Password CLI not authenticated"):
                driver.validate()

def test_secrets_driver_resolve_file(tmp_path):
    with patch("shutil.which", return_value="/usr/bin/op"):
        driver = SecretsDriver()
        env_file = tmp_path / "secrets.env"
        env_file.write_text("DB_PASSWORD=op://vault/db/password")
        
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(
                returncode=0, 
                stdout="DB_PASSWORD=secret-password\n"
            )
            
            import json
            result_json = driver._resolve_file(str(env_file))
            result = json.loads(result_json)
            assert result["DB_PASSWORD"] == "secret-password"

def test_technitium_driver_validate():
    with patch.dict(os.environ, {"TECHNITIUM_HOST": "http://dns.local", "TECHNITIUM_TOKEN": "token"}):
        driver = TechnitiumDriver()
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            mock_get.return_value.json.return_value = {"status": "ok"}
            assert driver.validate() is True

def test_technitium_driver_execute_record():
    with patch.dict(os.environ, {"TECHNITIUM_HOST": "http://dns.local", "TECHNITIUM_TOKEN": "token"}):
        driver = TechnitiumDriver()
        task = Task(
            type="provision",
            profile=MagicMock(),
            overrides={
                "resource": "record",
                "action": "create",
                "zone": "homelab.internal",
                "domain": "test.homelab.internal",
                "type": "A",
                "ipAddress": "192.168.1.10"
            }
        )
        with patch("requests.get") as mock_get:
            mock_get.return_value = MagicMock(status_code=200)
            mock_get.return_value.json.return_value = {"status": "ok"}
            result = driver.execute(task)
            assert result.success is True

def test_dns_service_provision_record():
    mock_driver = MagicMock()
    service = DNSService(driver=mock_driver)
    from homelab_gitops.domain.models import NodeProfile
    profile = NodeProfile(
        name="test-node",
        vcenter={"datacenter": "dc", "cluster": "cl", "datastore": "ds", "network": "nw"},
        vm_specs={"cpu": 1, "memory": 1024, "disk": "10GB"},
        deployment={"ip_address": "192.168.1.10", "vm_name_domain": "homelab.internal"}
    )
    
    mock_driver.execute.return_value = TaskResult(success=True, task_type="provision", output={}, duration=0.1)
    results = service.provision_record(profile)
    assert len(results) == 2
    assert results[0].success is True

def test_tofu_driver_validate():
    with patch.dict(os.environ, {"TOFU_WORKING_DIR": "/tmp"}):
        from homelab_gitops.drivers.tofu_driver import TofuDriver
        driver = TofuDriver()
        with patch("os.path.exists", return_value=True):
            assert driver.validate() is True

def test_ansible_driver_validate():
    with patch.dict(os.environ, {"ANSIBLE_PLAYBOOK_DIR": "/tmp"}):
        from homelab_gitops.drivers.ansible_driver import AnsibleDriver
        driver = AnsibleDriver()
        with patch("os.path.exists", return_value=True):
            assert driver.validate() is True

def test_vcenter_driver_validate():
    from homelab_gitops.drivers.vcenter_driver import vCenterDriver
    driver = vCenterDriver()
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        assert driver.validate() is True
        
        mock_run.return_value = MagicMock(returncode=1)
        from homelab_gitops.drivers.exceptions import PrerequisiteError
        with pytest.raises(PrerequisiteError):
            driver.validate()

def test_vcenter_driver_execute():
    from homelab_gitops.drivers.vcenter_driver import vCenterDriver
    driver = vCenterDriver()
    task = Task(type="test", profile=MagicMock())
    result = driver.execute(task)
    assert result.success is True
