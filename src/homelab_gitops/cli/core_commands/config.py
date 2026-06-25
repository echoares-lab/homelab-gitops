"""Config command - apply post-deployment OS configuration via Ansible."""

import os
import shutil
import subprocess
import sys
import time
import typer
import yaml
from typing import Optional
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.drivers.ansible_driver import AnsibleDriver
from homelab_gitops.drivers.secrets_driver import SecretsDriver
from homelab_gitops.domain.exceptions import DomainError
from homelab_gitops.cli.utils import print_success, print_error, print_info


def _run_in_background(args: list) -> None:
    """Wrap command in tmux session or nohup if tmux not available."""
    run_id = time.strftime("%Y-%m-%dT%H%M")
    session_name = f"bench-{run_id}"
    log_path = f"results/storage-benchmark/{run_id}/ansible.log"
    os.makedirs(f"results/storage-benchmark/{run_id}", exist_ok=True)

    if shutil.which("tmux"):
        cmd = ["tmux", "new-session", "-d", "-s", session_name, " ".join(args)]
        subprocess.run(cmd, check=True)
        print_info(f"Benchmark running in tmux session '{session_name}'")
        print_info(f"  Attach:  tmux attach -t {session_name}")
        print_info(f"  Monitor: watch cat results/storage-benchmark/{run_id}/summary.txt")
    else:
        with open(log_path, "w") as log:
            subprocess.Popen(args, stdout=log, stderr=log, start_new_session=True)
        print_info("Benchmark running in background (tmux not found)")
        print_info(f"  Log:     {log_path}")
        print_info(f"  Monitor: watch cat results/storage-benchmark/{run_id}/summary.txt")


def config_command(
    profile: str,
    index: Optional[str] = typer.Argument(None, help="Instance index (01, 02, etc.)"),
    background: bool = typer.Option(False, "--background", help="Run in tmux session (nohup fallback)"),
):
    """Apply post-deployment OS configuration via Ansible.

    Example:
        $ manage config ubuntu-base 01
        $ manage config benchmark-storage --background
    """
    if background:
        args = [sys.executable, "manage.py", "config", profile]
        if index:
            args.append(index)
        _run_in_background(args)
        return

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

        workflow = Workflow(profile_obj, drivers=drivers, secrets_driver=SecretsDriver())

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
