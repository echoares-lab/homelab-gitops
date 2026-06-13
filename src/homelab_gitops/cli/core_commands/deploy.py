"""Deploy command - provision VMs via OpenTofu."""

import os
import typer
import yaml
from typing import Optional
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.drivers.tofu_driver import TofuDriver
from homelab_gitops.domain.exceptions import DomainError
from homelab_gitops.cli.utils import print_success, print_error, print_info


def deploy_command(
    profile: str,
    index: Optional[str] = typer.Argument(None, help="Instance index (01, 02, etc.)"),
    host: Optional[str] = typer.Option(None, help="Target ESXi host"),
):
    """Provision virtual hardware via OpenTofu.

    Example:
        $ manage deploy ubuntu-base 01 --host esxi-01
    """
    try:
        # Load profile YAML
        profile_path = f"config/profiles/{profile}.yml"
        if not os.path.exists(profile_path):
            raise FileNotFoundError(f"Profile not found: {profile_path}")

        with open(profile_path) as f:
            profile_dict = yaml.safe_load(f)

        profile_dict["name"] = profile
        profile_obj = NodeProfile(**profile_dict)

        # Setup drivers
        drivers = {
            "deploy": TofuDriver(),
        }

        # Create workflow
        workflow = Workflow(profile_obj, drivers=drivers)

        # Execute deploy stage
        print_info(f"Deploying {profile} {index or ''} ...")
        state = workflow.execute(["deploy"])

        print_success(f"Deployed {profile} at {state.vm_ip}")

    except FileNotFoundError as e:
        print_error(str(e))
        raise typer.Exit(code=1)
    except DomainError as e:
        print_error(str(e))
        raise typer.Exit(code=1)
    except Exception as e:
        print_error(f"Deployment failed: {e}")
        raise typer.Exit(code=1)


# Plugin metadata
command_metadata = {
    "name": "deploy",
    "aliases": ["dep"],
    "help": "Provision virtual hardware via OpenTofu",
}
