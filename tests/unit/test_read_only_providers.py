from unittest.mock import MagicMock

from homelab_gitops.domain.models import NodeProfile, TaskResult
from homelab_gitops.providers.read_only import VCenterDriverStatusAdapter


def profile():
    return NodeProfile(
        name="test-profile",
        vcenter={"datacenter": "D", "cluster": "C", "datastore": "S", "network": "N"},
        vm_specs={"cpu": 1, "memory": 1, "disk": 1},
        deployment={"tags": [], "roles": [], "playbooks": []},
    )


def test_vcenter_status_adapter_maps_powered_on_result():
    driver = MagicMock()
    driver.execute.return_value = TaskResult(
        success=True,
        task_type="test",
        output="VM: test-profile, Power: poweredOn, IP: 10.0.0.1",
        duration=0.1,
        vm_ip="10.0.0.1",
    )

    status = VCenterDriverStatusAdapter(driver).get_vm_status(profile())

    assert status == {"provisioned": "Yes", "power": "On", "ip": "10.0.0.1"}
    task = driver.execute.call_args.args[0]
    assert task.type == "test"
    assert task.target == "test-profile"


def test_vcenter_status_adapter_preserves_legacy_unavailable_output():
    driver = MagicMock()
    driver.execute.return_value = TaskResult(
        success=False,
        task_type="test",
        output="VM powered off",
        duration=0.1,
    )

    status = VCenterDriverStatusAdapter(driver).get_vm_status(profile())

    assert status == {"provisioned": "No", "power": "N/A", "ip": "N/A"}
