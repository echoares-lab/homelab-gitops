import pytest
from unittest.mock import patch
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.immutable.transpilers.talos import TalosTranspiler
from homelab_gitops.drivers.exceptions import ExecutionError

@pytest.fixture
def talos_profile():
    profile_dict = {
        "name": "talos-node-01",
        "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"},
        "vm_specs": {"cpu": 4, "memory": 8192, "disk": 50},
        "deployment": {"tags": ["talos"]},
    }
    return NodeProfile(**profile_dict)

def test_talos_transpiler_success(talos_profile):
    transpiler = TalosTranspiler()
    
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/local/bin/talosctl"
        result = transpiler.transpile(talos_profile)
        
        assert "version: v1alpha1" in result
        assert "hostname: talos-node-01" in result

def test_talos_transpiler_missing_binary(talos_profile):
    transpiler = TalosTranspiler()
    
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None
        
        with pytest.raises(ExecutionError, match="talosctl not found in PATH"):
            transpiler.transpile(talos_profile)
