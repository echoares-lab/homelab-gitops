"""Build command - prepare base images."""

import os
import typer
import yaml
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.drivers.packer_driver import PackerDriver
from homelab_gitops.cli.utils import print_success, print_error, print_info


def build_command(
    profile: str = typer.Argument(..., help="Profile name to build"),
):
    """Prepare base images from templates.

    Example:
        $ manage build ubuntu-base
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
            "build": PackerDriver(),
        }

        # Create workflow
        workflow = Workflow(profile_obj, drivers=drivers)

        print_info(f"Building {profile} ...")
        workflow.execute(["build"])
        
        print_success(f"Build completed for {profile}")
    except Exception as e:
        print_error(f"Build failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "build",
    "aliases": ["bld"],
    "help": "Prepare base images from templates",
}
