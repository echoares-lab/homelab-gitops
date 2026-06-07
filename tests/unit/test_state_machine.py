from homelab_gitops.domain.state_machine import StateMachine
from homelab_gitops.domain.models import DeploymentState, TaskResult

def test_state_machine_valid_transition():
    """Valid transitions are allowed."""
    sm = StateMachine()
    assert sm.can_transition("planned", "deployed")
    assert sm.can_transition("deployed", "configured")

def test_state_machine_invalid_transition():
    """Invalid transitions are rejected."""
    sm = StateMachine()
    assert not sm.can_transition("planned", "tested")  # Can't test before deploy
    assert not sm.can_transition("tested", "deployed")  # Can't go backwards

def test_state_machine_update_state():
    """Transition updates DeploymentState."""
    sm = StateMachine()
    state = DeploymentState("ubuntu-base", "01", "ubuntu-base-01")
    result = TaskResult(success=True, task_type="deploy", output="...", duration=30.0, vm_ip="10.10.10.50")

    new_state = sm.transition(state, "deploy", result)
    assert new_state.state == "deployed"
    assert new_state.vm_ip == "10.10.10.50"
