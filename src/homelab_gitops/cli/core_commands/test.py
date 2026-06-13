"""Test command - validate deployment via testinfra."""

import os
import typer
import yaml
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.drivers.ansible_driver import AnsibleDriver
from homelab_gitops.cli.utils import print_success, print_error, print_info


def test_command(
    profile: str = typer.Argument(..., help="Profile name to test"),
):
    """Validate deployment via testinfra.

    Example:
        $ manage test ubuntu-base
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
            "test": AnsibleDriver(),
        }

        # Create workflow
        workflow = Workflow(profile_obj, drivers=drivers)

        print_info(f"Testing {profile} ...")
        workflow.execute(["test"])
        
        print_success(f"Tests passed for {profile}")
    except Exception as e:
        print_error(f"Test failed: {e}")
        raise typer.Exit(code=1)


command_metadata = {
    "name": "test",
    "aliases": ["tst"],
    "help": "Validate deployment via testinfra",
}
