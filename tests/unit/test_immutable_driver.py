import pytest
from homelab_gitops.domain.models import NodeProfile, Task
from homelab_gitops.immutable.drivers.immutable_driver import ImmutableDriver
from homelab_gitops.drivers.exceptions import ExecutionError

@pytest.fixture
def dummy_task():
    profile_dict = {
        "name": "dummy",
        "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"},
        "vm_specs": {"cpu": 4, "memory": 8192, "disk": 50},
        "deployment": {"tags": []},
    }
    profile = NodeProfile(**profile_dict)
    return Task(type="config", profile=profile, target="10.10.10.10", overrides={})

def test_immutable_driver_validate():
    driver = ImmutableDriver()
    assert driver.validate() is True

def test_immutable_driver_execute_valid_stage(dummy_task):
    driver = ImmutableDriver()
    result = driver.execute(dummy_task)
    
    assert result.success is True
    assert result.task_type == "config"
    assert "boot injection" in result.output

def test_immutable_driver_execute_invalid_stage(dummy_task):
    driver = ImmutableDriver()
    dummy_task.type = "deploy" # Not config or configure
    
    with pytest.raises(ExecutionError, match="only overrides config"):
        driver.execute(dummy_task)
