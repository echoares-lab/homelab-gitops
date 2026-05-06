#!/usr/bin/env python3
import argparse
import os
import sys
import subprocess
import time
import re
import yaml
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.status import Status
from rich.panel import Panel

console = Console()

# --- HELPER FUNCTIONS ---

def load_env(env_file="config/secrets.env"):
    if not os.path.exists(env_file):
        console.print(f"[bold red]Error:[/bold red] '{env_file}' not found.")
        console.print("[yellow]Hint:[/yellow] Copy 'config/secrets.env.example' to 'config/secrets.env' and fill in your credentials.")
        sys.exit(1)
        
    with open(env_file, 'r') as f:
        content = f.read()
        if "REDACTED" in content:
            console.print(f"[bold red]Error:[/bold red] '{env_file}' contains REDACTED values.")
            console.print("[yellow]Hint:[/yellow] Open the file and replace REDACTED placeholders with real credentials.")
            sys.exit(1)
            
        for line in content.splitlines():
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' in line:
                key, val = line.split('=', 1)
                val = val.split(' #')[0].strip() # Remove inline comments
                val = val.strip('"\'') # Remove quotes
                os.environ[key.strip()] = val

def track_time(start_time, task_name):
    duration = int(time.time() - start_time)
    console.print(f"[bold green]Task [{task_name}][/bold green] completed in {duration // 60}m {duration % 60}s")

def validate_mac(mac):
    if mac and not re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", mac):
        console.print(f"[bold red]Error:[/bold red] Invalid MAC address format ({mac}). Expected xx:xx:xx:xx:xx:xx")
        sys.exit(1)

def run_cmd(cmd, cwd=None, capture=False):
    res = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=capture)
    if res.returncode != 0 and not capture:
        sys.exit(res.returncode)
    return res

def identify_vm(target):
    with console.status("[bold blue]Identifying VM..."):
        # 1. Check for exact workspace match
        res = run_cmd("tofu workspace list", cwd="tofu", capture=True)
        for line in res.stdout.splitlines():
            ws = line.replace('*', '').strip()
            if ws == target:
                return ws

        # 2. Check by IP
        if re.match(r"^([0-9]{1,3}\.){3}[0-9]{1,3}$", target):
            govc_cmd = f"./build/govc find . -type m -guest.ipAddress '{target}'"
            res = run_cmd(govc_cmd, capture=True)
            if res.returncode == 0 and res.stdout.strip():
                return os.path.basename(res.stdout.strip().splitlines()[0])

        # 3. Check for partial name match
        res = run_cmd("tofu workspace list", cwd="tofu", capture=True)
        for line in res.stdout.splitlines():
            ws = line.replace('*', '').strip()
            if target in ws:
                return ws
    return None

def get_vm_ip():
    if not os.path.exists('ansible/inventory.ini'):
        console.print("[bold red]Error:[/bold red] ansible/inventory.ini not found. Cannot determine IP.")
        sys.exit(1)
    with open('ansible/inventory.ini', 'r') as f:
        content = f.read()
        match = re.search(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', content)
        if match:
            return match.group(1)
    console.print("[bold red]Error:[/bold red] Could not extract IP from inventory.ini")
    sys.exit(1)

# --- COMMAND LOGIC ---

def cmd_build(args):
    start = time.time()
    console.print(Panel(f"Building Golden OVF Template via Packer ({args.profile})", style="blue"))
    if "ubuntu" in args.profile:
        console.print("[bold red]Error:[/bold red] Ubuntu packer build not yet integrated. Use govc capture method.")
        sys.exit(1)
    packer_file = "packer/photon.pkr.hcl"

    # Map remaining consolidated vars to Packer
    os.environ["PKR_VAR_vcenter_server"] = os.environ.get("VCENTER_SERVER", "")
    os.environ["PKR_VAR_vcenter_username"] = os.environ.get("VCENTER_USERNAME", "")
    os.environ["PKR_VAR_vcenter_password"] = os.environ.get("VCENTER_PASSWORD", "")
    os.environ["PKR_VAR_datacenter"] = os.environ.get("VCENTER_DATACENTER", "")
    os.environ["PKR_VAR_cluster"] = os.environ.get("VCENTER_CLUSTER", "")
    os.environ["PKR_VAR_datastore"] = os.environ.get("VCENTER_DATASTORE", "")
    os.environ["PKR_VAR_network"] = os.environ.get("VCENTER_NETWORK", "")
    os.environ["PKR_VAR_photon_iso_url"] = os.environ.get("PHOTON_ISO_URL", "")
    os.environ["PKR_VAR_photon_iso_checksum"] = os.environ.get("PHOTON_ISO_CHECKSUM", "")
    os.environ["PKR_VAR_ssh_username"] = os.environ.get("SSH_ADMIN_USERNAME", "")
    os.environ["PKR_VAR_ssh_password"] = os.environ.get("SSH_ADMIN_PASSWORD", "")

    run_cmd(f"packer init {packer_file}")
    run_cmd(f"packer build -var-file=\"config/secrets.env\" {packer_file}")
    track_time(start, "Packer Build")

def cmd_lint(args):
    start = time.time()
    console.print(Panel(f"Configuration Linting for {args.profile} targeting {args.host}", style="blue"))
    os.environ["RUNTIME_PROFILE"] = args.profile
    os.environ["VCENTER_HOST_OVER_RIDE"] = args.host # Note: lint_config script expects VCENTER_HOST_OVERRIDE (fixing typo in script or here?)
    # Fix: manage.sh uses VCENTER_HOST_OVERRIDE.
    os.environ["VCENTER_HOST_OVERRIDE"] = args.host
    run_cmd("python3 scripts/lint_config.py")
    track_time(start, "Linting")

def load_profile_to_env(profile_name, args):
    profile_path = f"config/profiles/{profile_name}.yml"
    if not os.path.exists(profile_path):
        console.print(f"[bold red]Error:[/bold red] Profile {profile_path} not found.")
        sys.exit(1)
    
    with open(profile_path, 'r') as f:
        c = yaml.safe_load(f)

    os.environ["TF_VAR_datacenter"] = c["vcenter"].get("datacenter", "")
    os.environ["TF_VAR_cluster"] = c["vcenter"].get("cluster", "")
    os.environ["TF_VAR_datastore"] = c["vcenter"].get("datastore", "")
    os.environ["TF_VAR_network"] = c["vcenter"].get("network", "")
    os.environ["TF_VAR_vm_cpu"] = str(c["vm_specs"].get("cpu", ""))
    os.environ["TF_VAR_vm_ram_gb"] = str(c["vm_specs"].get("ram_gb", ""))
    os.environ["TF_VAR_guest_id"] = c["vm_specs"].get("guest_id", "")
    os.environ["TF_VAR_disk_size_gb"] = str(c["vm_specs"].get("disk_size_gb", ""))
    os.environ["TF_VAR_library_name"] = c["content_library"].get("name", "")
    os.environ["TF_VAR_template_name"] = c["content_library"].get("template", "")
    os.environ["TF_VAR_vm_tags"] = '["' + '","'.join(c["deployment"].get("tags", [])) + '"]'
    
    yaml_mac = c["deployment"].get("mac_address", "")
    mac = args.mac if args.mac else yaml_mac
    os.environ["TF_VAR_mac_address"] = mac
    
    os.environ["TF_VAR_ipv4_address"] = args.ip or ""
    os.environ["TF_VAR_ipv4_netmask"] = str(args.netmask)
    os.environ["TF_VAR_ipv4_gateway"] = args.gateway or ""
    os.environ["TF_VAR_dns_servers"] = f'["{args.dns}"]'

    vm_domain = c["deployment"].get("vm_name_domain", "local")
    vm_prefix = c["deployment"].get("vm_name_prefix", "node")
    
    if args.hostname:
        vm_name = f"{args.hostname}.{vm_domain}"
    else:
        vm_name = f"{vm_prefix}-{args.id}.{vm_domain}"
        
    os.environ["TF_VAR_vm_name"] = vm_name
    return vm_name, c["deployment"].get("tags", [])

def cmd_deploy(args):
    start = time.time()
    console.print(Panel(f"Unified OpenTofu Deployment ({args.profile})", style="blue"))
    
    vm_name, _ = load_profile_to_env(args.profile, args)
    
    os.environ["TF_VAR_vcenter_server"] = os.environ.get("VCENTER_SERVER", "")
    os.environ["TF_VAR_vcenter_user"] = os.environ.get("VCENTER_USERNAME", "")
    os.environ["TF_VAR_vcenter_password"] = os.environ.get("VCENTER_PASSWORD", "")
    os.environ["TF_VAR_host"] = args.host
    
    console.print(f"[blue]Targeting VM:[/blue] {vm_name}")
    if args.ip:
        console.print(f"[blue]Static IP:[/blue] {args.ip}")

    run_cmd("tofu init", cwd="tofu")
    if run_cmd(f"tofu workspace select '{vm_name}'", cwd="tofu", capture=True).returncode != 0:
        run_cmd(f"tofu workspace new '{vm_name}'", cwd="tofu")
    
    run_cmd("tofu apply -auto-approve", cwd="tofu")
    
    res = run_cmd("tofu output -raw vm_ip", cwd="tofu", capture=True)
    vm_ip = res.stdout.strip()
    console.print(f"[bold green]VM Deployed at {vm_ip}[/bold green]")
    
    run_cmd(f"python3 ../scripts/test_connectivity.py '{vm_ip}'", cwd="tofu")
    
    with open("ansible/inventory.ini", "w") as f:
        f.write(f"node ansible_host={vm_ip} ansible_user={os.environ.get('SSH_ADMIN_USERNAME', 'ansible')}\n")
    
    track_time(start, "Deployment")

def cmd_config(args):
    start = time.time()
    console.print(Panel("Tag-Based Ansible Configuration", style="blue"))
    
    limit_arg = ""
    # Implied Limits Logic
    if args.id and args.id != "01": 
        vm_name, _ = load_profile_to_env(args.profile, args)
        limit_arg = f"-l {vm_name}"
        console.print(f"[yellow]Auto-Filter:[/yellow] Instance ({vm_name})")
    else:
        profile_path = f"config/profiles/{args.profile}.yml"
        if os.path.exists(profile_path):
            with open(profile_path, 'r') as f:
                c = yaml.safe_load(f)
                tags = c.get("deployment", {}).get("tags", [])
                if tags:
                    primary_tag = tags[0]
                    limit_arg = f"-l tag_{primary_tag}"
                    console.print(f"[yellow]Auto-Filter:[/yellow] Profile group (tag_{primary_tag})")
        if not limit_arg:
            console.print("[yellow]Auto-Filter:[/yellow] None (Broad Deployment)")

    os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    ssh_key = os.environ.get("SSH_PRIVATE_KEY_PATH", "")
    ssh_pass = os.environ.get("SSH_ADMIN_PASSWORD", "")
    
    ansible_cmd = f"ansible-playbook -i inventory/vmware_vms.yml site.yml {limit_arg} "
    ansible_cmd += f"--private-key '{ssh_key}' --extra-vars \"ansible_ssh_pass={ssh_pass}\" "
    ansible_cmd += f"--ssh-extra-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'"
    
    run_cmd(ansible_cmd, cwd="ansible")
    track_time(start, "Ansible Configuration")

def cmd_test(args):
    start = time.time()
    console.print(Panel(f"End-to-End Testing for {args.profile}", style="blue"))
    vm_ip = get_vm_ip()
    
    console.print(f"[blue]Running pytest against {vm_ip} using unified test suite...[/blue]")
    if args.mac:
        os.environ["EXPECTED_MAC"] = args.mac
        
    ssh_key = os.environ.get("SSH_PRIVATE_KEY_PATH", "")
    pytest_cmd = f"pytest --hosts='ansible@{vm_ip}' --ssh-config='/dev/null' "
    pytest_cmd += f"--ssh-extra-args='-o StrictHostKeyChecking=no -o IdentityFile={ssh_key}' "
    pytest_cmd += f"--sudo tests/test_common.py tests/test_os.py"
    
    run_cmd(pytest_cmd)
    track_time(start, "E2E Testing")

def cmd_destroy(args):
    if args.keep:
        console.print("[yellow]Keep flag set. Skipping destruction phase.[/yellow]")
        return
        
    start = time.time()
    if hasattr(args, 'identifier') and args.identifier:
        target_id = args.identifier
    else:
        vm_name, _ = load_profile_to_env(args.profile, args)
        target_id = vm_name

    console.print(f"[bold red]Identifying VM for destruction:[/bold red] {target_id}...")
    resolved_name = identify_vm(target_id)
    
    if not resolved_name:
        console.print(f"[bold red]Error:[/bold red] Could not identify a managed VM matching '{target_id}'.")
        sys.exit(1)
        
    if not Confirm.ask(f"\n[bold red]WARNING:[/bold red] Are you sure you want to permanently destroy '[bold cyan]{resolved_name}[/bold cyan]'?"):
        console.print("[yellow]Destruction cancelled.[/yellow]")
        return

    console.print(f"[red]Destroying Workspace:[/red] {resolved_name}")
    run_cmd(f"tofu workspace select '{resolved_name}'", cwd="tofu")
    
    destroy_cmd = (
        f"tofu destroy -auto-approve -refresh=false "
        f"-var=\"vcenter_server={os.environ.get('VCENTER_SERVER')}\" "
        f"-var=\"vcenter_user={os.environ.get('VCENTER_USERNAME')}\" "
        f"-var=\"vcenter_password={os.environ.get('VCENTER_PASSWORD')}\" "
        f"-var=\"datacenter=x\" -var=\"cluster=x\" -var=\"host=x\" "
        f"-var=\"datastore=x\" -var=\"network=x\" -var=\"vm_name={resolved_name}\" "
        f"-var=\"vm_cpu=1\" -var=\"vm_ram_gb=1\" -var=\"guest_id=x\" "
        f"-var=\"library_name=x\" -var=\"template_name=x\" -var=\"vm_tags=x\""
    )
    run_cmd(destroy_cmd, cwd="tofu")
    run_cmd("tofu workspace select default", cwd="tofu")
    run_cmd(f"tofu workspace delete '{resolved_name}'", cwd="tofu")
    track_time(start, "Destruction")

def cmd_all(args):
    total_start = time.time()
    cmd_lint(args)
    cmd_deploy(args)
    cmd_config(args)
    cmd_test(args)
    if not args.keep:
        cmd_destroy(args)
    track_time(total_start, "TOTAL SYNTHESIS PIPELINE")

def interactive_mode():
    console.print(Panel("HomeLab GitOps Command Builder", style="bold magenta"))
    
    commands = ["build", "lint", "deploy", "config", "test", "destroy", "all", "create-profile", "edit-profile", "create-role", "create-play", "Quit"]
    i_command = Prompt.ask("Select Command", choices=commands)
    
    if i_command == "Quit":
        sys.exit(0)

    if i_command in ["create-profile", "edit-profile", "create-role", "create-play"]:
        if i_command == "create-profile": run_cmd("python3 scripts/profile_manager.py create")
        if i_command == "edit-profile": run_cmd("python3 scripts/profile_manager.py edit")
        if i_command == "create-role": run_cmd("python3 scripts/role_manager.py")
        if i_command == "create-play": run_cmd("python3 scripts/play_manager.py")
        sys.exit(0)

    if i_command == "destroy":
        i_id = Prompt.ask("\nEnter VM Name, IP, or MAC to destroy")
        if i_id:
            run_cmd(f"python3 manage.py destroy {i_id}")
        sys.exit(0)

    profiles = [f.replace('.yml','') for f in os.listdir("config/profiles") if f.endswith('.yml')]
    i_profile = Prompt.ask("Select Profile", choices=profiles)
    i_id = Prompt.ask("Instance ID", default="01")

    flags = ""
    i_host = Prompt.ask("Override Host? (Leave empty for default)", default="")
    if i_host: flags += f" --host {i_host}"

    i_ip = Prompt.ask("Set Static IP? (empty for DHCP)", default="")
    if i_ip:
        flags += f" --ip {i_ip}"
        i_gw = Prompt.ask("  Gateway", default="10.10.10.1")
        flags += f" --gateway {i_gw}"

    i_mac = Prompt.ask("Custom MAC? (xx:xx...)", default="")
    if i_mac: flags += f" --mac {i_mac}"

    full_cmd = f"python3 manage.py {i_command} {i_profile} {i_id} {flags}".strip()
    console.print(f"\n[bold green]Constructed Command:[/bold green] {full_cmd}")
    console.print("-" * 40)
    run_cmd(full_cmd)
    console.print(f"\n[bold green]Execution Summary:[/bold green] {full_cmd}")
    sys.exit(0)

# --- MAIN ---

def main():
    if len(sys.argv) == 1:
        interactive_mode()

    parser = argparse.ArgumentParser(description="Unified HomeLab GitOps Orchestrator")
    parser.add_argument('-k', '--keep', action='store_true', help="Skip 'destroy' phase")
    
    subparsers = parser.parse_known_args() # We use manual subshell logic to avoid argparse subparser complexity for now
    
    # Simple manual subparser logic for Rich compatibility
    command = sys.argv[1] if len(sys.argv) > 1 else None
    
    parser = argparse.ArgumentParser(description="Unified HomeLab GitOps Orchestrator")
    parser.add_argument('-k', '--keep', action='store_true')
    parser.add_argument('command', choices=["build", "lint", "deploy", "config", "test", "destroy", "all", "create-profile", "edit-profile", "create-role", "create-play"])
    parser.add_argument('profile', nargs='?', default='photon-docker')
    parser.add_argument('id', nargs='?', default='01')
    parser.add_argument('--host', default='esxi-01.mgmt.plexplease.com')
    parser.add_argument('--mac', default='')
    parser.add_argument('--ip', default='')
    parser.add_argument('--hostname', default='')
    parser.add_argument('--netmask', default='24')
    parser.add_argument('--gateway', default='')
    parser.add_argument('--dns', default='8.8.8.8')
    parser.add_argument('identifier', nargs='?', default='') # For destroy

    # Special handling for 'destroy <identifier>'
    if command == "destroy" and len(sys.argv) > 2 and not sys.argv[2].startswith('-'):
        # Re-parse but treat sys.argv[2] as identifier
        pass

    args = parser.parse_args()

    # Pre-flight checks
    load_env("config/secrets.env")
    
    os.environ["VMWARE_HOST"] = os.environ.get("VCENTER_SERVER", "")
    os.environ["VMWARE_USER"] = os.environ.get("VCENTER_USERNAME", "")
    os.environ["VMWARE_PASSWORD"] = os.environ.get("VCENTER_PASSWORD", "")
    os.environ["VMWARE_VALIDATE_CERTS"] = "no"

    validate_mac(args.mac)

    if args.command == "build": cmd_build(args)
    elif args.command == "lint": cmd_lint(args)
    elif args.command == "deploy": cmd_deploy(args)
    elif args.command == "config": cmd_config(args)
    elif args.command == "test": cmd_test(args)
    elif args.command == "destroy": 
        # Fix identifier for destroy
        if args.profile and not args.identifier:
            args.identifier = args.profile
        cmd_destroy(args)
    elif args.command == "all": cmd_all(args)
    elif args.command == "create-profile": run_cmd("python3 scripts/profile_manager.py create")
    elif args.command == "edit-profile": run_cmd("python3 scripts/profile_manager.py edit")
    elif args.command == "create-role": run_cmd("python3 scripts/role_manager.py")
    elif args.command == "create-play": run_cmd("python3 scripts/play_manager.py")

if __name__ == "__main__":
    main()
