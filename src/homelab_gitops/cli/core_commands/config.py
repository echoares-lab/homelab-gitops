"""Config command - apply post-deployment OS configuration via Ansible."""

import os
import typer
import yaml
from typing import Optional
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.drivers.ansible_driver import AnsibleDriver
from homelab_gitops.domain.exceptions import DomainError
from homelab_gitops.cli.utils import print_success, print_error, print_info


def config_command(
    profile: str,
    index: Optional[str] = typer.Argument(None, help="Instance index (01, 02, etc.)"),
):
    """Apply post-deployment OS configuration via Ansible.

    Example:
        $ manage config ubuntu-base 01
    """
    try:
        profile_path = f"config/profiles/{profile}.yml"
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path) as f:
            profile_dict = yaml.safe_load(f)

        profile_dict["name"] = profile
        profile_obj = NodeProfile(**profile_dict)

        drivers = {
            "config": AnsibleDriver(),
        }

        workflow = Workflow(profile_obj, drivers=drivers)

        print_info(f"Configuring {profile} {index or 'all instances'} ...")
        state = workflow.execute(["config"])

        print_success(f"Configuration applied to {state.vm_name}")

    except Exception as e:
        print_error(f"Configuration failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "config",
    "aliases": ["cfg"],
    "help": "Apply Ansible configuration to nodes",
}
