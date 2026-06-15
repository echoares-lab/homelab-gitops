"""Network generation CLI plugin."""
import typer
from typing import Optional
from homelab_gitops.domain.network import NetworkService
from homelab_gitops.cli.utils import print_success, print_error, print_info

app = typer.Typer(help="Manage networking and auto-registration (DNS, DHCP, MAC)")

@app.command()
def generate(
    profile: str = typer.Argument(..., help="Profile name (e.g. ubuntu-base)"),
    index: str = typer.Argument("01", help="Instance index (01, 02, etc.)"),
    domain: str = typer.Option("mgmt.plexplease.com", help="Domain/Subdomain for the record"),
    dhcp_scope: str = typer.Option("10.10.10.0", help="DHCP Scope Network address"),
    ip: Optional[str] = typer.Option(None, help="Specific IP to assign. Auto-selects if not provided.")
):
    """Generate MAC, IP, A, and PTR records for a VM."""
    svc = NetworkService()
    mac = svc.generate_mac()
    hostname = f"{profile}-{index}"
    
    assigned_ip = ip or svc.get_next_ip(dhcp_scope)
    if not assigned_ip:
        print_error("Could not determine next IP. Please provide --ip.")
        raise typer.Exit(code=1)
        
    print_info(f"Generating networking for {hostname}:")
    print_info(f"  MAC Address : {mac}")
    print_info(f"  IP Address  : {assigned_ip}")
    print_info(f"  Domain      : {domain}")
    print_info(f"  DHCP Scope  : {dhcp_scope}")
    
    try:
        svc.append_dns_records(mac, assigned_ip, hostname, domain, dhcp_scope, f"Auto-generated for {hostname}")
        print_success(f"Successfully appended records to config/dns_records.csv")
    except Exception as e:
        print_error(f"Failed to write records: {e}")
        raise typer.Exit(code=1)

@app.command("mass-generate")
def mass_generate(
    profile: str = typer.Argument(..., help="Profile name"),
    count: int = typer.Argument(..., help="Number of instances to generate"),
    start_index: int = typer.Option(1, help="Starting index (e.g. 1 -> 01)"),
    domain: str = typer.Option("mgmt.plexplease.com", help="Domain/Subdomain"),
    dhcp_scope: str = typer.Option("10.10.10.0", help="DHCP Scope Network address")
):
    """Mass generate MAC, IP, and DNS records for multiple instances."""
    svc = NetworkService()
    print_info(f"Mass generating {count} instances for {profile}...")
    
    for i in range(start_index, start_index + count):
        index_str = f"{i:02d}"
        hostname = f"{profile}-{index_str}"
        mac = svc.generate_mac()
        assigned_ip = svc.get_next_ip(dhcp_scope)
        
        if not assigned_ip:
            print_error(f"Could not determine next IP for {hostname}. Stopping.")
            break
            
        svc.append_dns_records(mac, assigned_ip, hostname, domain, dhcp_scope, f"Mass-generated for {hostname}")
        print_success(f"Generated {hostname} -> {assigned_ip} ({mac})")

def network_command() -> typer.Typer:
    return app

# Plugin metadata
command_metadata = {
    "name": "network",
    "aliases": ["net"],
    "help": "Auto-generate and manage networking assignments (DNS/DHCP/MAC)",
    "is_app": True
}
