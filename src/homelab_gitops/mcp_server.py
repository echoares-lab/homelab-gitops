"""Model Context Protocol server for Homelab-GitOps."""

import os
import yaml
from typing import Optional

from mcp.server.fastmcp import FastMCP

from homelab_gitops.domain.models import NodeProfile
from homelab_gitops.domain.status import StatusService
from homelab_gitops.domain.certificate import CertificateService
from homelab_gitops.domain.workflows import Workflow
from homelab_gitops.drivers.vcenter_driver import vCenterDriver
from homelab_gitops.drivers.tofu_driver import TofuDriver
from homelab_gitops.drivers.ansible_driver import AnsibleDriver
from homelab_gitops.drivers.acme_driver import AcmeDriver
from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
from homelab_gitops.drivers.secrets_driver import SecretsDriver

mcp = FastMCP("Homelab-GitOps")

@mcp.tool()
def get_fleet_status() -> str:
    """Get the status of all nodes in the fleet."""
    try:
        profiles_dir = "config/profiles"
        if not os.path.exists(profiles_dir):
            return "Error: config/profiles directory not found."

        profiles = []
        for filename in os.listdir(profiles_dir):
            if filename.endswith(".yml") or filename.endswith(".yaml"):
                profile_path = os.path.join(profiles_dir, filename)
                with open(profile_path) as f:
                    profile_dict = yaml.safe_load(f)
                
                profile_name = os.path.splitext(filename)[0]
                profile_dict["name"] = profile_name
                profiles.append(NodeProfile(**profile_dict))

        status_service = StatusService(vCenterDriver(), TofuDriver())
        fleet_status = status_service.get_fleet_status(profiles)
        
        output = []
        for status in fleet_status:
            output.append(f"Profile: {status['name']}")
            output.append(f"  Provisioned: {status['provisioned']}")
            output.append(f"  Power: {status['power']}")
            output.append(f"  IP: {status['ip']}")
            output.append(f"  Drift: {status['drift']}")
            output.append("")
            
        return "\n".join(output) if output else "No profiles found."
    except Exception as e:
        return f"Error getting fleet status: {str(e)}"

@mcp.tool()
def issue_certificate(domain: str, email: str) -> str:
    """Issue a certificate for a domain using ACME DNS-01."""
    try:
        cert_service = CertificateService(
            AcmeDriver(),
            TechnitiumDriver(),
            SecretsDriver()
        )
        cert_pem = cert_service.issue_certificate(domain, email)
        return f"Successfully issued certificate for {domain}:\n{cert_pem}"
    except Exception as e:
        return f"Error issuing certificate: {str(e)}"

@mcp.tool()
def deploy_vm(profile_name: str, index: Optional[str] = None) -> str:
    """Deploy and configure a VM based on a profile."""
    try:
        profile_path = f"config/profiles/{profile_name}.yml"
        if not os.path.exists(profile_path):
            return f"Error: Profile not found: {profile_path}"

        with open(profile_path) as f:
            profile_dict = yaml.safe_load(f)

        profile_dict["name"] = profile_name
        profile_obj = NodeProfile(**profile_dict)

        drivers = {
            "deploy": TofuDriver(),
            "config": AnsibleDriver(),
        }

        workflow = Workflow(profile_obj, drivers=drivers, secrets_driver=SecretsDriver())
        state = workflow.execute(["deploy", "config"])
        
        return f"Successfully deployed and configured {profile_name}. IP: {state.vm_ip}"
    except Exception as e:
        return f"Error deploying VM: {str(e)}"

if __name__ == "__main__":
    mcp.run()
