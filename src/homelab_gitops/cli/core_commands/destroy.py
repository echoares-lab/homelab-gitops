"""Destroy command - tear down infrastructure."""

import os
import typer
import yaml
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.drivers.tofu_driver import TofuDriver
from homelab_gitops.cli.utils import print_success, print_error, print_info


def destroy_command(
    profile: str = typer.Argument(..., help="Profile name to destroy"),
):
    """Tear down virtual infrastructure via OpenTofu.

    Example:
        $ manage destroy ubuntu-base
    """
    try:
        profile_path = f"config/profiles/{profile}.yml"
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path) as f:
            profile_dict = yaml.safe_load(f)

        profile_dict["name"] = profile
        profile_obj = NodeProfile(**profile_dict)

        # Setup drivers
        drivers = {
            "destroy": TofuDriver(),
        }

        # Create workflow
        workflow = Workflow(profile_obj, drivers=drivers)

        print_info(f"Destroying {profile} ...")
        workflow.execute(["destroy"])
        
        print_success(f"Destroyed {profile}")
    except Exception as e:
        print_error(f"Destroy failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "destroy",
    "aliases": ["des"],
    "help": "Tear down virtual infrastructure via OpenTofu",
}
