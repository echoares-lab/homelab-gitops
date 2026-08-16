"""Immutable OS Workflow orchestration."""

import os
from typing import Dict, List, Any
from homelab_gitops.domain.models import NodeProfile, Task, TaskResult, DeploymentState
from homelab_gitops.domain.state_machine import StateMachine
from homelab_gitops.domain.exceptions import InvalidStateTransition, DomainError
from homelab_gitops.domain.validators import YAMLSchemaValidator

class ImmutableWorkflow:
    """Orchestrates the Build → Transpile → Provision → Verify pipeline."""

    def __init__(
        self,
        profile: NodeProfile,
        drivers: Dict[str, Any],
        secrets_driver: Any = None,
        immutable_config_driver: Any = None,
    ):
        self.profile = profile
        self.drivers = drivers
        self.secrets_driver = secrets_driver
        self.immutable_config_driver = immutable_config_driver
        self.state_machine = StateMachine()
        self.state = DeploymentState(
            profile_name=profile.name,
            index="",
            vm_name=profile.name,
        )

        validator = YAMLSchemaValidator()
        result = validator.validate(profile)
        if not result.success:
            raise DomainError(f"Profile validation failed: {result.errors}")

    def execute(self, stages: List[str]) -> DeploymentState:
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
            next_state = stage_to_state.get(stage, stage)

            if not self.state_machine.can_transition(self.state.state, next_state):
                raise InvalidStateTransition(self.state.state, stage)

            # Route to correct driver based on immutable needs
            driver = self.drivers.get(stage)
            if stage in ["config", "configure"]:
                # Bypass standard Ansible driver for immutable
                driver = self.immutable_config_driver or driver
            
            if not driver:
                raise DomainError(f"No driver for stage: {stage}")

            task = self._prepare_task(stage)

            try:
                result = driver.execute(task)
            except Exception as e:
                self.state = self.state_machine.transition_to_failed(self.state, str(e))
                raise

            self.state = self.state_machine.transition(self.state, stage, result)

        return self.state

    def _prepare_task(self, stage: str) -> Task:
        # Same preparation logic as standard workflow, but can inject transpiled payloads
        overrides = {}
        overrides["profile_name"] = self.profile.name
        overrides["vm_name"] = self.profile.deployment.get("vm_name", self.state.vm_name)
        
        # In a full implementation, if stage == 'deploy', we would transpile the config here
        # and attach it to the overrides dict so Tofu can inject it.
        if stage == "deploy":
            os_type = self.profile.vcenter.get("os_type", "")
            if os_type == "fcos":
                from homelab_gitops.immutable.transpilers.butane import ButaneTranspiler
                payload = ButaneTranspiler().transpile(self.profile)
                overrides["ignition_data"] = payload
                overrides["os_type"] = "fcos"
            elif os_type == "talos":
                from homelab_gitops.immutable.transpilers.talos import TalosTranspiler
                payload = TalosTranspiler().transpile(self.profile)
                overrides["machine_config"] = payload
                overrides["os_type"] = "talos"
                
        # Load secrets through an injected provider when available.
        try:
            if not self.secrets_driver:
                raise DomainError("No secrets provider configured")
            vcenter_user = self.secrets_driver.execute(Task(type="get", target="bao://kv/agents/autonomous/vcenter/prod/VCENTER_USERNAME")).output
            vcenter_pass = self.secrets_driver.execute(Task(type="get", target="bao://kv/agents/autonomous/vcenter/prod/VCENTER_PASSWORD")).output
            vcenter_server = self.secrets_driver.execute(Task(type="get", target="bao://kv/agents/autonomous/vcenter/prod/VCENTER_SERVER")).output
        except Exception:
            vcenter_user = os.environ.get("VCENTER_USER", "administrator@vsphere.local")
            vcenter_pass = os.environ.get("VCENTER_PASSWORD", "")
            vcenter_server = os.environ.get("VCENTER_SERVER", "")
            
        overrides["vcenter_server"] = vcenter_server or self.profile.vcenter.get("host", "")
        overrides["vcenter_user"] = vcenter_user or os.environ.get("VCENTER_USER", "administrator@vsphere.local")
        overrides["vcenter_username"] = overrides["vcenter_user"]
        overrides["vcenter_password"] = vcenter_pass or os.environ.get("VCENTER_PASSWORD", "")

        # Fill rest of standard overrides
        overrides["datacenter"] = self.profile.vcenter.get("datacenter", "")
        overrides["cluster"] = self.profile.vcenter.get("cluster", "")
        overrides["datastore"] = self.profile.vcenter.get("datastore", "")
        overrides["network"] = self.profile.vcenter.get("network", "")
        
        return Task(
            type=stage,
            profile=self.profile,
            target=self.state.vm_ip,
            overrides=overrides
        )
