from typing import Dict, List, Any
from homelab_gitops.domain.models import NodeProfile, Task, DeploymentState
from homelab_gitops.domain.state_machine import StateMachine
from homelab_gitops.domain.exceptions import InvalidStateTransition, DomainError
from homelab_gitops.domain.validators import YAMLSchemaValidator


class Workflow:
    """Orchestrates the Build → Provision → Configure → Test pipeline."""

    def __init__(self, profile: NodeProfile, drivers: Dict[str, Any]):
        """Initialize workflow for a profile.

        Args:
            profile: NodeProfile to deploy
            drivers: Dict of {stage: Driver} for execute
        """
        self.profile = profile
        self.drivers = drivers
        self.state_machine = StateMachine()
        self.state = DeploymentState(
            profile_name=profile.name,
            index="",
            vm_name=profile.name,
        )

        # Validate profile structure
        validator = YAMLSchemaValidator()
        result = validator.validate(profile)
        if not result.success:
            raise DomainError(f"Profile validation failed: {result.errors}")

    def execute(self, stages: List[str]) -> DeploymentState:
        """Execute stages in order, updating state machine.

        Args:
            stages: List of stages to run (e.g., ["deploy", "config", "test"])

        Returns:
            Final DeploymentState after all stages

        Raises:
            InvalidStateTransition: if stage is not allowed from current state
            DriverError: if any driver fails
        """
        # Map stage name to resulting state
        stage_to_state = {
            "build": "built",
            "deploy": "deployed",
            "provision": "deployed",  # Alias
            "config": "configured",
            "configure": "configured",  # Alias
            "test": "tested",
            "destroy": "destroyed",
        }

        for stage in stages:
            # Map stage to resulting state
            next_state = stage_to_state.get(stage, stage)

            # Check state machine allows this transition
            if not self.state_machine.can_transition(self.state.state, next_state):
                raise InvalidStateTransition(self.state.state, stage)

            # Prepare task
            task = self._prepare_task(stage)

            # Execute via driver
            driver = self.drivers.get(stage)
            if not driver:
                raise DomainError(f"No driver for stage: {stage}")

            try:
                result = driver.execute(task)
            except Exception as e:
                # Transition to failed state
                self.state = self.state_machine.transition_to_failed(self.state, str(e))
                raise

            # Update state
            self.state = self.state_machine.transition(self.state, stage, result)

        return self.state

    def _prepare_task(self, stage: str) -> Task:
        """Prepare a task for the given stage."""
        return Task(
            type=stage,
            profile=self.profile,
            target=self.state.vm_ip,
        )
