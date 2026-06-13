import copy

from homelab_gitops.domain.models import DeploymentState, TaskResult

class StateMachine:
    """Enforces valid state transitions for node lifecycle."""

    TRANSITIONS = {
        "planned": ["deployed"],
        "deployed": ["configured", "destroyed"],
        "configured": ["tested", "destroyed"],
        "tested": ["updated", "destroyed"],
        "failed": ["destroyed"],
    }

    def can_transition(self, current: str, next_stage: str) -> bool:
        """Check if transition from current to next_stage is valid."""
        return next_stage in self.TRANSITIONS.get(current, [])

    def transition(self, state: DeploymentState, stage: str, result: TaskResult) -> DeploymentState:
        """Update state after successful stage execution."""
        # Map stage name to new state
        stage_to_state = {
            "build": "built",
            "deploy": "deployed",
            "provision": "deployed",  # Alias
            "config": "configured",
            "configure": "configured",  # Alias
            "test": "tested",
            "destroy": "destroyed",
        }

        new_state_name = stage_to_state.get(stage, stage)

        # Update the state
        new_state = copy.copy(state)
        new_state.state = new_state_name
        if result.vm_ip:
            new_state.vm_ip = result.vm_ip
        return new_state

    def transition_to_failed(self, state: DeploymentState, error: str) -> DeploymentState:
        """Mark state as failed with error message."""
        new_state = copy.copy(state)
        new_state.state = "failed"
        new_state.error = error
        return new_state
