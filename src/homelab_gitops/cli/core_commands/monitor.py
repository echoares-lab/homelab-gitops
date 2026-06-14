"""Monitor command - manage observability and monitoring."""

import os
import typer
import yaml
from rich.console import Console
from homelab_gitops.domain.observability import ObservabilityService
from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.cli.utils import print_success, print_error, print_info

app = typer.Typer(help="Manage observability and monitoring")
console = Console()

def monitor_command():
    """Entry point for the monitor command group."""
    return app

def _load_profile(profile_name: str) -> NodeProfile:
    """Helper to load a NodeProfile from YAML."""
    profile_path = os.path.join("config", "profiles", f"{profile_name}.yml")
    if not os.path.exists(profile_path):
        raise FileNotFoundError(f"Profile not found: {profile_path}")
        
    with open(profile_path) as f:
        p_dict = yaml.safe_load(f)
        
    p_dict["name"] = profile_name
    return NodeProfile(**p_dict)

@app.command(name="setup")
def setup(profile: str = typer.Argument(..., help="Profile name to setup monitoring for")):
    """Deploy monitoring stack to a node."""
    print_info(f"Setting up monitoring for profile: {profile}...")
    try:
        node_profile = _load_profile(profile)
        service = ObservabilityService()
        result = service.deploy_monitoring(node_profile)
        
        if result.success:
            print_success(f"Successfully deployed monitoring to {profile}")
        else:
            print_error(f"Failed to deploy monitoring: {result.error}")
            raise typer.Exit(code=1)
            
    except Exception as e:
        print_error(f"Setup failed: {e}")
        raise typer.Exit(code=1)

@app.command(name="health")
def health(profile: str = typer.Argument(..., help="Profile name to check health for")):
    """Get metrics and health status for a node."""
    print_info(f"Checking health for profile: {profile}...")
    try:
        node_profile = _load_profile(profile)
        service = ObservabilityService()
        metrics = service.get_metrics(node_profile)
        
        status = metrics.get("status", "unknown")
        if status == "ok":
            print_success(f"Health check passed for {profile}")
        else:
            print_error(f"Health check failed for {profile}: {status}")
            
        console.print(metrics)
        
    except Exception as e:
        print_error(f"Health check failed: {e}")
        raise typer.Exit(code=1)

command_metadata = {
    "name": "monitor",
    "aliases": ["mon"],
    "help": "Manage observability and monitoring",
    "is_app": True
}
