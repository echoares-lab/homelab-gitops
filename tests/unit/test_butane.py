import pytest
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.immutable.transpilers.butane import ButaneTranspiler
from homelab_gitops.drivers.exceptions import ExecutionError
import json
import yaml

def test_butane_transpiler_network(monkeypatch):
    profile = NodeProfile(
        name="fcos-test",
        vcenter={"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"},
        vm_specs={"cpu": 4, "memory": 8192, "disk": 80},
        deployment={
            "tags": ["fcos"],
            "ip_address": "10.10.10.9",
            "ipv4_netmask": 24,
            "ipv4_gateway": "10.10.10.1",
            "dns_servers": ["10.10.10.2", "1.1.1.1"],
        },
    )
    
    transpiler = ButaneTranspiler()
    
    # We want to intercept the YAML input before it's passed to subprocess.run
    captured_yaml = None
    
    def mock_run(args, input, capture_output):
        nonlocal captured_yaml
        captured_yaml = yaml.safe_load(input.decode('utf-8'))
        
        class MockResult:
            returncode = 0
            stdout = b'{"mocked": "json"}'
            
        return MockResult()
        
    def mock_which(cmd):
        return "/usr/bin/butane"
        
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("shutil.which", mock_which)
    
    transpiler.transpile(profile)
    
    # Verify the YAML payload that would have been passed to Butane
    assert captured_yaml is not None
    files = captured_yaml.get("storage", {}).get("files", [])
    
    nm_file = next((f for f in files if f.get("path") == "/etc/NetworkManager/system-connections/ens192.nmconnection"), None)
    assert nm_file is not None
    assert nm_file["mode"] == 384  # 0600
    
    contents = nm_file["contents"]["inline"]
    assert "addresses=10.10.10.9/24" in contents
    assert "gateway=10.10.10.1" in contents
    assert "dns=10.10.10.2;1.1.1.1;" in contents

def test_butane_transpiler_no_network(monkeypatch):
    profile = NodeProfile(
        name="fcos-test",
        vcenter={"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"},
        vm_specs={"cpu": 4, "memory": 8192, "disk": 80},
        deployment={
            "tags": ["fcos"],
        },
    )
    
    transpiler = ButaneTranspiler()
    
    captured_yaml = None
    
    def mock_run(args, input, capture_output):
        nonlocal captured_yaml
        captured_yaml = yaml.safe_load(input.decode('utf-8'))
        
        class MockResult:
            returncode = 0
            stdout = b'{"mocked": "json"}'
            
        return MockResult()
        
    def mock_which(cmd):
        return "/usr/bin/butane"
        
    monkeypatch.setattr("subprocess.run", mock_run)
    monkeypatch.setattr("shutil.which", mock_which)
    
    transpiler.transpile(profile)
    
    # Verify the YAML payload that would have been passed to Butane
    assert captured_yaml is not None
    files = captured_yaml.get("storage", {}).get("files", [])
    
    nm_file = next((f for f in files if f.get("path") == "/etc/NetworkManager/system-connections/ens192.nmconnection"), None)
    assert nm_file is None
