import os
from typing import Dict, List, Any
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult, DeploymentState
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
            "provision": "deployed",
            "config": "configured",
            "configure": "configured",
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
        overrides = {}
        
        # Map profile variables to Tofu variables
        overrides["profile_name"] = self.profile.name
        overrides["vm_name"] = self.state.vm_name
        
        # vCenter
        overrides["datacenter"] = self.profile.vcenter.get("datacenter", "")
        overrides["cluster"] = self.profile.vcenter.get("cluster", "")
        overrides["host"] = self.profile.vcenter.get("host", "")
        overrides["datastore"] = self.profile.vcenter.get("datastore", "")
        overrides["network"] = self.profile.vcenter.get("network", "")
        
        # Load secrets via SecretsDriver
        from homelab_gitops.drivers.secrets_driver import SecretsDriver
        from homelab_gitops.domain.models import Task as SecretsTask
        try:
            secrets_driver = SecretsDriver()
            vcenter_user = secrets_driver.execute(SecretsTask(type="get", target="bao://kv/prod/platform/vcenter/VCENTER_USERNAME")).output
            vcenter_pass = secrets_driver.execute(SecretsTask(type="get", target="bao://kv/prod/platform/vcenter/VCENTER_PASSWORD")).output
            vcenter_server = secrets_driver.execute(SecretsTask(type="get", target="bao://kv/prod/platform/vcenter/VCENTER_SERVER")).output
        except Exception:
            vcenter_user = os.environ.get("VCENTER_USER", "administrator@vsphere.local")
            vcenter_pass = os.environ.get("VCENTER_PASSWORD", "")
            vcenter_server = os.environ.get("VCENTER_SERVER", "")
            
        overrides["vcenter_server"] = vcenter_server or self.profile.vcenter.get("host", "")
        overrides["vcenter_user"] = vcenter_user or os.environ.get("VCENTER_USER", "administrator@vsphere.local")
        overrides["vcenter_password"] = vcenter_pass or os.environ.get("VCENTER_PASSWORD", "")
        
        # Content Library
        overrides["library_name"] = self.profile.content_library.get("name", "")
        overrides["template_name"] = self.profile.content_library.get("template", "")
        
        # VM Specs
        overrides["vm_cpu"] = self.profile.vm_specs.get("cpu", 2)
        # Convert memory from MB to GB (vm_specs stores in MB, provider expects GB)
        memory_mb = self.profile.vm_specs.get("memory", 8192)
        overrides["vm_ram_gb"] = memory_mb // 1024  # Convert MB to GB
        overrides["disk_size_gb"] = self.profile.vm_specs.get("disk", 50)
        overrides["guest_id"] = self.profile.vm_specs.get("guest_id", "")
        
        # Deployment
        tags = self.profile.deployment.get("tags", [])
        overrides["vm_tags"] = ",".join(tags) if tags else ""

        if "mac_address" in self.profile.deployment:
            overrides["mac_address"] = self.profile.deployment["mac_address"]
        if "ip_address" in self.profile.deployment:
            overrides["ipv4_address"] = self.profile.deployment["ip_address"]

        return Task(
            type=stage,
            profile=self.profile,
            target=self.state.vm_ip,
            overrides=overrides
        )
