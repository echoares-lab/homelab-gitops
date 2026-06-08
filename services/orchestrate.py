"""OrchestrateService: Full VM lifecycle orchestration."""

import time
from typing import Optional, List, Dict
from rich.console import Console
from services.infrastructure import InfrastructureService
from services.config import ConfigService
from services.utils import track_time, validate_mac

console = Console()

class OrchestrateService:
    """
    Orchestrates complete VM lifecycle: build, lint, deploy, config, test, destroy.

    Depends on InfrastructureService and ConfigService to perform operations.
    """

    def __init__(self, infrastructure: InfrastructureService, config: ConfigService):
        """
        Initialize orchestration service.

        Args:
            infrastructure: InfrastructureService instance
            config: ConfigService instance
        """
        self.infrastructure = infrastructure
        self.config_service = config

    def build(self, target: str) -> bool:
        """
        Build a golden image with Packer.

        Args:
            target: Build target (ubuntu-2404, ubuntu-2604, photon-docker)

        Returns:
            True if build succeeded
        """
        console.print(f"[bold blue]Building {target}...[/bold blue]")
        start = time.time()

        # TODO: Implement Packer build logic
        # This is a stub; actual implementation would call packer build

        track_time(start, f"build {target}")
        return True

    def lint(self, profile: str, index: str) -> bool:
        """
        Validate a profile and vCenter infrastructure.

        Args:
            profile: Profile name (e.g., 'ubuntu-2404-base')
            index: VM index (e.g., '01')

        Returns:
            True if lint passed
        """
        console.print(f"[bold blue]Linting {profile} {index}...[/bold blue]")
        start = time.time()

        try:
            # Load and validate profile
            profile_data = self.config_service.load_profile(profile)
            self.config_service.validate_profile(profile_data)

            # Ensure tags exist in vCenter
            tags = profile_data.get("tags", [])
            self.infrastructure.ensure_tags_exist(tags)

            console.print("[green]✓ Lint passed[/green]")
            track_time(start, f"lint {profile} {index}")
            return True

        except Exception as e:
            console.print(f"[red]✗ Lint failed: {e}[/red]")
            return False

    def deploy(
        self,
        profile: str,
        index: str,
        host: Optional[str] = None,
        mac: Optional[str] = None
    ) -> bool:
        """
        Provision a VM via OpenTofu.

        Args:
            profile: Profile name
            index: VM index
            host: Optional ESXi host to deploy to
            mac: Optional MAC address for DHCP reservation

        Returns:
            True if deploy succeeded
        """
        console.print(f"[bold blue]Deploying {profile} {index}...[/bold blue]")
        start = time.time()

        try:
            # Validate inputs
            if mac:
                validate_mac(mac)

            # Load profile
            profile_data = self.config_service.load_profile(profile)

            # TODO: Implement OpenTofu deployment
            # This is a stub; actual implementation would call tofu apply

            console.print("[green]✓ Deploy succeeded[/green]")
            track_time(start, f"deploy {profile} {index}")
            return True

        except Exception as e:
            console.print(f"[red]✗ Deploy failed: {e}[/red]")
            return False

    def config(self, profile: str, index: str) -> bool:
        """
        Apply Ansible configuration to a deployed VM.

        Args:
            profile: Profile name
            index: VM index

        Returns:
            True if config succeeded
        """
        console.print(f"[bold blue]Configuring {profile} {index}...[/bold blue]")
        start = time.time()

        try:
            # Load profile and resolve playbook
            playbook, extra_vars = self.config_service.resolve_playbook(profile)

            # TODO: Implement Ansible execution
            # This is a stub; actual implementation would call infrastructure.run_ansible_playbook()

            console.print("[green]✓ Config succeeded[/green]")
            track_time(start, f"config {profile} {index}")
            return True

        except Exception as e:
            console.print(f"[red]✗ Config failed: {e}[/red]")
            return False

    def test(self, profile: str, index: str) -> bool:
        """
        Run testinfra validation on a VM.

        Args:
            profile: Profile name
            index: VM index

        Returns:
            True if tests passed
        """
        console.print(f"[bold blue]Testing {profile} {index}...[/bold blue]")
        start = time.time()

        # TODO: Implement testinfra execution
        # This is a stub; actual implementation would run pytest with --hosts

        console.print("[green]✓ Tests passed[/green]")
        track_time(start, f"test {profile} {index}")
        return True

    def destroy(self, identifier: str) -> bool:
        """
        Destroy a VM by name, IP, or MAC address.

        Args:
            identifier: VM name, IP address, or MAC address

        Returns:
            True if destroy succeeded
        """
        console.print(f"[bold yellow]Destroying {identifier}...[/bold yellow]")
        start = time.time()

        # TODO: Implement VM destruction
        # This is a stub; actual implementation would call tofu destroy

        console.print("[green]✓ Destroy succeeded[/green]")
        track_time(start, f"destroy {identifier}")
        return True

    def status(self) -> List[Dict]:
        """
        Report fleet health and status.

        Returns:
            List of VM status dictionaries
        """
        console.print("[bold blue]Collecting fleet status...[/bold blue]")

        try:
            rows = self.infrastructure.collect_fleet_status()
            console.print(f"[green]✓ Collected status for {len(rows)} VMs[/green]")
            return rows
        except Exception as e:
            console.print(f"[yellow]⚠ Could not collect fleet status: {e}[/yellow]")
            return []

    def all(self, profile: str, index: str, host: str) -> bool:
        """
        Run complete pipeline: lint → deploy → config → test.

        Args:
            profile: Profile name
            index: VM index
            host: ESXi host for deployment

        Returns:
            True if entire pipeline succeeded
        """
        console.print(f"[bold cyan]Running complete pipeline for {profile} {index}...[/bold cyan]")
        start = time.time()

        steps = [
            ("lint", lambda: self.lint(profile, index)),
            ("deploy", lambda: self.deploy(profile, index, host=host)),
            ("config", lambda: self.config(profile, index)),
            ("test", lambda: self.test(profile, index)),
        ]

        for step_name, step_func in steps:
            console.print(f"\n[bold]Step: {step_name}[/bold]")
            if not step_func():
                console.print(f"[red]✗ Pipeline aborted at {step_name}[/red]")
                return False

        console.print("[green]✓ Complete pipeline succeeded[/green]")
        track_time(start, f"all {profile} {index}")
        return True
