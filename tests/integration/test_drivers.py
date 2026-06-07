import pytest
from homelab_gitops.drivers.base import Driver
from homelab_gitops.domain.models import Task, TaskResult, NodeProfile


def test_driver_is_abstract():
    """Driver is abstract base class."""
    with pytest.raises(TypeError):
        Driver()


def test_concrete_driver_interface():
    """Concrete drivers implement execute() and validate()."""
    class DummyDriver(Driver):
        def execute(self, task: Task) -> TaskResult:
            return TaskResult(
                success=True,
                task_type=task.type,
                output="success",
                duration=1.0,
            )

        def validate(self) -> bool:
            return True

    driver = DummyDriver()
    assert driver.validate()

    profile_dict = {
        "name": "test",
        "vcenter": {"datacenter": "DC", "cluster": "C", "datastore": "DS", "network": "N"},
        "vm_specs": {"cpu": 1, "memory": 1024, "disk": 10},
        "deployment": {},
    }
    profile = NodeProfile(**profile_dict)
    task = Task(type="test", profile=profile)
    result = driver.execute(task)
    assert result.success
