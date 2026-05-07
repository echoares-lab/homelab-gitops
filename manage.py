#!/usr/bin/env python3
import os
import sys
import subprocess
import time
import re
import yaml
import json
from typing import Optional, List
from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich import print as rprint

# Initialize Typer and Rich
app = typer.Typer(
    help="Unified HomeLab GitOps Orchestrator",
    add_completion=False,
    rich_markup_mode="rich"
)
console = Console()

# --- GLOBALS & METADATA ---
METADATA_FILE = "config/metadata.yml"
metadata = {
    "commands": {},
    "tags": {},
    "roles": {}
}

if os.path.exists(METADATA_FILE):
    with open(METADATA_FILE, 'r') as f:
        metadata = yaml.safe_load(f)

# --- HELPER FUNCTIONS ---

def load_vault(vault_file="config/vault.yml"):
    """Loads infrastructure secrets into the environment from Ansible Vault."""
    if not os.path.exists(vault_file):
        console.print(f"[bold red]Error:[/bold red] '{vault_file}' not found.")
        console.print("[yellow]Hint:[/yellow] Copy 'config/vault.yml.example' to 'config/vault.yml', edit it, and encrypt it with 'ansible-vault encrypt config/vault.yml'.")
        sys.exit(1)
        
    vault_pass_file = "config/.vault_pass"
    if not os.path.exists(vault_pass_file):
        console.print(f"[bold red]Error:[/bold red] '{vault_pass_file}' not found.")
        console.print("[yellow]Hint:[/yellow] Create 'config/.vault_pass' containing your Ansible Vault password.")
        sys.exit(1)

    # Use ansible-vault to decrypt the file
    res = subprocess.run(f"ansible-vault view {vault_file} --vault-password-file {vault_pass_file}", shell=True, text=True, capture_output=True)
    if res.returncode != 0:
        console.print(f"[bold red]Error:[/bold red] Failed to decrypt '{vault_file}'. Check your vault password.")
        sys.exit(1)
        
    content = res.stdout
    if "REDACTED" in content:
        console.print(f"[bold red]Error:[/bold red] '{vault_file}' contains REDACTED values.")
        console.print("[yellow]Hint:[/yellow] Decrypt the file, replace REDACTED placeholders, and re-encrypt.")
        sys.exit(1)
        
    try:
        secrets = yaml.safe_load(content)
        if secrets:
            for key, val in secrets.items():
                os.environ[key.upper()] = str(val)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] Failed to parse decrypted YAML: {e}")
        sys.exit(1)

def track_time(start_time, task_name):
    """Calculates and prints the duration of a task."""
    duration = int(time.time() - start_time)
    console.print(f"[bold green]Task [{task_name}][/bold green] completed in {duration // 60}m {duration % 60}s")

def validate_mac(mac: Optional[str]):
    """Ensures MAC address follows the xx:xx:xx:xx:xx:xx format."""
    if mac and not re.match(r"^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$", mac):
        console.print(f"[bold red]Error:[/bold red] Invalid MAC address format ({mac}).")
        sys.exit(1)

def ensure_tags_exist(tags: List[str]):
    """Checks and creates vSphere tags using govc."""
    if not tags:
        return

    env = os.environ.copy()
    env["GOVC_URL"] = env.get("VCENTER_SERVER")
    env["GOVC_USERNAME"] = env.get("VCENTER_USERNAME")
    env["GOVC_PASSWORD"] = env.get("VCENTER_PASSWORD")
    env["GOVC_INSECURE"] = "true"
    govc_path = "/home/gemini-cli/template-pipeline/build/govc"

    with console.status("[bold blue]Ensuring vCenter tags exist..."):
        # 1. Ensure category exists
        res = subprocess.run([govc_path, "tags.category.ls"], capture_output=True, text=True, env=env)
        if "Provisioning" not in res.stdout:
            console.print("[yellow]Creating tag category 'Provisioning'...[/yellow]")
            subprocess.run([govc_path, "tags.category.create", "Provisioning"], env=env)

        # 2. Ensure each tag exists
        res = subprocess.run([govc_path, "tags.ls", "-c", "Provisioning"], capture_output=True, text=True, env=env)
        for t in tags:
            if t not in res.stdout:
                console.print(f"[yellow]Creating vCenter tag '{t}' in category 'Provisioning'...[/yellow]")
                subprocess.run([govc_path, "tags.create", "-c", "Provisioning", t], env=env)

def run_cmd(cmd, cwd=None, capture=False):
    """Executes a shell command via subprocess."""
    res = subprocess.run(cmd, shell=True, cwd=cwd, text=True, capture_output=capture)
    if res.returncode != 0 and not capture:
        sys.exit(res.returncode)
    return res

def identify_vm(target: str):
    """Discovers a VM Name/Workspace using an IP, MAC, or Partial Name."""
    with console.status(f"[bold blue]Identifying VM for '{target}'..."):
        # 1. Direct Workspace Match
        res = run_cmd("tofu workspace list", cwd="tofu", capture=True)
        for line in res.stdout.splitlines():
            ws = line.replace('*', '').strip()
            if ws == target:
                return ws

        # 2. Query vCenter by IP
        if re.match(r"^([0-9]{1,3}\.){3}[0-9]{1,3}$", target):
            govc_cmd = f"./build/govc find . -type m -guest.ipAddress '{target}'"
            res = run_cmd(govc_cmd, capture=True)
            if res.returncode == 0 and res.stdout.strip():
                return os.path.basename(res.stdout.strip().splitlines()[0])

        # 3. Partial Workspace Match
        res = run_cmd("tofu workspace list", cwd="tofu", capture=True)
        for line in res.stdout.splitlines():
            ws = line.replace('*', '').strip()
            if target in ws:
                return ws
    return None

def get_vm_ip():
    """Extracts the VM IP from the Ansible temporary inventory."""
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

def load_profile_to_env(profile: str, id: str, host: str, mac: str, ip: str, hostname: str, netmask: str, gateway: str, dns: str):
    """Maps YAML profile data and CLI overrides to OpenTofu environment variables."""
    profile_path = f"config/profiles/{profile}.yml"
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
    os.environ["TF_VAR_vm_tags"] = ",".join(c["deployment"].get("tags", []))
    
    yaml_mac = c["deployment"].get("mac_address", "")
    os.environ["TF_VAR_mac_address"] = mac if mac else yaml_mac
    os.environ["TF_VAR_ipv4_address"] = ip or ""
    os.environ["TF_VAR_ipv4_netmask"] = str(netmask)
    os.environ["TF_VAR_ipv4_gateway"] = gateway or ""
    os.environ["TF_VAR_dns_servers"] = f'["{dns}"]'
    os.environ["TF_VAR_host"] = host

    vm_domain = c["deployment"].get("vm_name_domain", "local")
    vm_prefix = c["deployment"].get("vm_name_prefix", "node")
    
    if hostname:
        vm_name = hostname if "." in hostname else f"{hostname}.{vm_domain}"
    else:
        vm_name = f"{vm_prefix}-{id}.{vm_domain}"
    
    os.environ["TF_VAR_vm_name"] = vm_name
    return vm_name, c["deployment"].get("tags", [])

# --- CLI COMMANDS ---

@app.command()
def build(
    profile: Annotated[str, typer.Argument(help="Profile to build")] = "photon-docker"
):
    """[blue]Packer:[/blue] Build a fresh Golden OVF template."""
    start = time.time()
    console.print(Panel(f"Building Golden OVF Template via Packer ({profile})", style="blue"))
    if "ubuntu" in profile:
        console.print("[bold red]Error:[/bold red] Ubuntu packer build not yet integrated. Use govc capture method.")
        sys.exit(1)
    
    packer_file = "packer/photon.pkr.hcl"
    # Inject Consolidated Environment
    for var in ["VCENTER_SERVER", "VCENTER_USERNAME", "VCENTER_PASSWORD", "VCENTER_DATACENTER", "VCENTER_CLUSTER", "VCENTER_DATASTORE", "VCENTER_NETWORK", "PHOTON_ISO_URL", "PHOTON_ISO_CHECKSUM", "SSH_ADMIN_USERNAME", "SSH_ADMIN_PASSWORD"]:
        os.environ[f"PKR_VAR_{var.lower()}"] = os.environ.get(var, "")

    run_cmd(f"packer init {packer_file}")
    run_cmd(f"packer build {packer_file}")
    track_time(start, "Packer Build")

@app.command()
def lint(
    profile: Annotated[str, typer.Argument(help="Profile to lint")] = "photon-docker",
    id: Annotated[Optional[str], typer.Argument(help="Instance ID (Optional)")] = "01",
    host: Annotated[str, typer.Option(help="Override target ESXi host")] = "esxi-01.mgmt.plexplease.com"
):
    """[blue]Audit:[/blue] Validate YAML schema and vCenter objects."""
    start = time.time()
    console.print(Panel(f"Configuration Linting for {profile} targeting {host}", style="blue"))
    os.environ["RUNTIME_PROFILE"] = profile
    os.environ["VCENTER_HOST_OVERRIDE"] = host
    run_cmd("python3 scripts/lint_config.py")
    track_time(start, "Linting")

@app.command()
def deploy(
    profile: Annotated[str, typer.Argument(help="Profile to deploy")] = "photon-docker",
    id: Annotated[str, typer.Argument(help="Instance ID")] = "01",
    host: Annotated[str, typer.Option(help="Override target host")] = "esxi-01.mgmt.plexplease.com",
    mac: Annotated[str, typer.Option(help="Override MAC")] = "",
    ip: Annotated[str, typer.Option(help="Set static IP")] = "",
    hostname: Annotated[str, typer.Option(help="Override hostname")] = "",
    netmask: Annotated[str, typer.Option(help="Subnet bits")] = "24",
    gateway: Annotated[str, typer.Option(help="Default gateway")] = "",
    dns: Annotated[str, typer.Option(help="Primary DNS")] = "8.8.8.8"
):
    """[blue]Provision:[/blue] Deploy virtual hardware via OpenTofu."""
    start = time.time()
    console.print(Panel(f"Unified OpenTofu Deployment ({profile})", style="blue"))
    
    vm_name, tags = load_profile_to_env(profile, id, host, mac, ip, hostname, netmask, gateway, dns)
    ensure_tags_exist(tags)
    
    os.environ["TF_VAR_vcenter_server"] = os.environ.get("VCENTER_SERVER", "")
    os.environ["TF_VAR_vcenter_user"] = os.environ.get("VCENTER_USERNAME", "")
    os.environ["TF_VAR_vcenter_password"] = os.environ.get("VCENTER_PASSWORD", "")
    
    console.print(f"[blue]Targeting VM:[/blue] {vm_name}")
    if tags:
        table = Table(title="Associated Tags", box=None)
        table.add_column("Tag", style="cyan")
        table.add_column("Description", style="white")
        for t in tags:
            table.add_row(t, metadata["tags"].get(t, "No description available."))
        console.print(table)

    run_cmd("tofu init", cwd="tofu")
    if run_cmd(f"tofu workspace select '{vm_name}'", cwd="tofu", capture=True).returncode != 0:
        run_cmd(f"tofu workspace new '{vm_name}'", cwd="tofu")
    
    run_cmd("tofu apply -auto-approve", cwd="tofu")
    vm_ip = run_cmd("tofu output -raw vm_ip", cwd="tofu", capture=True).stdout.strip()
    console.print(f"[bold green]VM Deployed at {vm_ip}[/bold green]")
    
    run_cmd(f"python3 ../scripts/test_connectivity.py '{vm_ip}'", cwd="tofu")
    with open("ansible/inventory.ini", "w") as f:
        f.write(f"node ansible_host={vm_ip} ansible_user={os.environ.get('SSH_ADMIN_USERNAME', 'ansible')}\n")
    track_time(start, "Deployment")

@app.command()
def config(
    profile: Annotated[str, typer.Argument(help="Profile to configure")] = "photon-docker",
    id: Annotated[Optional[str], typer.Argument(help="Instance ID for strict targeting")] = None
):
    """[blue]Configure:[/blue] Apply Ansible roles (Auto-Limited by Profile/ID)."""
    start = time.time()
    console.print(Panel("Tag-Based Ansible Configuration", style="blue"))
    
    limit_arg = ""
    if id:
        vm_name, _ = load_profile_to_env(profile, id, "", "", "", "", "24", "", "8.8.8.8")
        limit_arg = f"-l {vm_name}"
        console.print(f"[yellow]Auto-Filter:[/yellow] Instance ({vm_name})")
    else:
        profile_path = f"config/profiles/{profile}.yml"
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
    
    ansible_cmd = (
        f"ansible-playbook -i inventory/vmware_vms.yml site.yml {limit_arg} "
        f"--private-key '{ssh_key}' --extra-vars \"ansible_ssh_pass={ssh_pass}\" "
        f"--ssh-extra-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'"
    )
    run_cmd(ansible_cmd, cwd="ansible")
    track_time(start, "Ansible Configuration")

@app.command()
def test(
    profile: Annotated[str, typer.Argument(help="Profile to test")] = "photon-docker",
    mac: Annotated[str, typer.Option(help="Expected MAC address")] = ""
):
    """[blue]Verify:[/blue] Run automated Pytest-Testinfra validation."""
    start = time.time()
    console.print(Panel(f"End-to-End Testing for {profile}", style="blue"))
    vm_ip = get_vm_ip()
    
    if mac: os.environ["EXPECTED_MAC"] = mac
    ssh_key = os.environ.get("SSH_PRIVATE_KEY_PATH", "")
    pytest_cmd = (
        f"pytest --hosts='ansible@{vm_ip}' --ssh-config='/dev/null' "
        f"--ssh-extra-args='-o StrictHostKeyChecking=no -o IdentityFile={ssh_key}' "
        f"--sudo tests/test_common.py tests/test_os.py"
    )
    run_cmd(pytest_cmd)
    track_time(start, "E2E Testing")

@app.command()
def destroy(
    identifier: Annotated[str, typer.Argument(help="VM Name, IP, or MAC")] = "",
    keep: Annotated[bool, typer.Option("--keep", "-k", help="Skip destruction")] = False,
    auto_approve: Annotated[bool, typer.Option("--yes", "-y", help="Bypass confirmation")] = False
):
    """[blue]Teardown:[/blue] Remove VM and its isolated Tofu state."""
    if keep:
        console.print("[yellow]Keep flag set. Skipping destruction phase.[/yellow]")
        return
        
    start = time.time()
    if not identifier:
        console.print("[bold red]Error:[/bold red] 'destroy' requires an identifier (Name, IP, or MAC).")
        sys.exit(1)

    console.print(f"[bold red]Identifying VM for destruction:[/bold red] {identifier}...")
    resolved_name = identify_vm(identifier)
    
    if not resolved_name:
        console.print(f"[bold red]Error:[/bold red] Could not identify a managed VM matching '{identifier}'.")
        sys.exit(1)
        
    if not auto_approve:
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

@app.command()
def all(
    profile: Annotated[str, typer.Argument(help="Profile to deploy")] = "photon-docker",
    id: Annotated[str, typer.Argument(help="Instance ID")] = "01",
    host: Annotated[str, typer.Option(help="ESXi host")] = "esxi-01.mgmt.plexplease.com",
    mac: Annotated[str, typer.Option(help="Custom MAC")] = "",
    ip: Annotated[str, typer.Option(help="Static IP")] = "",
    hostname: Annotated[str, typer.Option(help="Hostname override")] = "",
    netmask: Annotated[str, typer.Option(help="Netmask")] = "24",
    gateway: Annotated[str, typer.Option(help="Gateway")] = "",
    dns: Annotated[str, typer.Option(help="DNS")] = "8.8.8.8",
    keep: Annotated[bool, typer.Option("--keep", "-k", help="Skip destruction")] = False
):
    """[blue]Synthesis:[/blue] Execute the full pipeline (Lint -> Deploy -> Config -> Test -> Destroy)."""
    total_start = time.time()
    
    # Internal CLI invocation to reuse logic
    lint(profile, host)
    deploy(profile, id, host, mac, ip, hostname, netmask, gateway, dns)
    config(profile, id)
    test(profile, mac)
    if not keep:
        vm_name, _ = load_profile_to_env(profile, id, host, mac, ip, hostname, netmask, gateway, dns)
        destroy(vm_name)
        
    track_time(total_start, "TOTAL SYNTHESIS PIPELINE")

# --- GENERATORS ---

@app.command()
def create_profile():
    """[blue]Generator:[/blue] Scaffold a new YAML configuration profile."""
    run_cmd("python3 scripts/profile_manager.py create")

@app.command()
def edit_profile():
    """[blue]Generator:[/blue] Update an existing profile."""
    run_cmd("python3 scripts/profile_manager.py edit")

@app.command()
def create_role():
    """[blue]Generator:[/blue] Scaffold a new Ansible role."""
    run_cmd("python3 scripts/role_manager.py")

@app.command()
def create_play():
    """[blue]Generator:[/blue] Create a new targeting bucket in site.yml."""
    run_cmd("python3 scripts/play_manager.py")

# --- INTERACTIVE MODE ---

def interactive_mode():
    console.print(Panel.fit("HomeLab GitOps Command Builder", style="bold magenta", border_style="cyan"))
    
    cmd_table = Table(show_header=True, header_style="bold cyan", box=None)
    cmd_table.add_column("Command", style="bold white")
    cmd_table.add_column("Description", style="italic")
    
    core_cmds = ["build", "lint", "deploy", "config", "test", "destroy", "all"]
    gen_cmds = ["create-profile", "edit-profile", "create-role", "create-play"]
    
    for c in core_cmds + gen_cmds:
        desc = metadata["commands"].get(c, "No description.")
        cmd_table.add_row(c, desc)
    
    console.print(cmd_table)
    i_command = Prompt.ask("\nSelect Command", choices=core_cmds + gen_cmds + ["Quit"])
    if i_command == "Quit": sys.exit(0)

    # Generators
    if i_command in gen_cmds:
        func_map = {
            "create-profile": create_profile, "edit-profile": edit_profile,
            "create-role": create_role, "create-play": create_play
        }
        func_map[i_command]()
        sys.exit(0)

    # Destruction (Special path for single identifier)
    if i_command == "destroy":
        i_id = Prompt.ask("\nEnter VM Name, IP, or MAC to destroy")
        if i_id: destroy(identifier=i_id)
        sys.exit(0)

    # Profile Selection
    profiles = [f.replace('.yml','') for f in os.listdir("config/profiles") if f.endswith('.yml')]
    p_table = Table(show_header=True, header_style="bold green", box=None)
    p_table.add_column("Profile", style="bold white")
    p_table.add_column("Tags", style="cyan")
    p_table.add_column("Specs", style="dim")

    for p in profiles:
        with open(f"config/profiles/{p}.yml", 'r') as f:
            c = yaml.safe_load(f)
            tags = ",".join(c["deployment"].get("tags", []))
            specs = f"{c['vm_specs']['cpu']}vCPU / {c['vm_specs']['ram_gb']}GB RAM"
            p_table.add_row(p, tags, specs)
    
    console.print("\nAvailable Profiles:")
    console.print(p_table)
    i_profile = Prompt.ask("Select Profile", choices=profiles)
    i_id = Prompt.ask("Instance ID", default="01")

    # Overrides
    overrides = {}
    console.print("\n[dim]Optional Overrides (Press Enter to skip):[/dim]")
    overrides['host'] = Prompt.ask("Override Target Host", default="esxi-01.mgmt.plexplease.com")
    overrides['ip'] = Prompt.ask("Set Static IP (e.g. 10.10.10.50)", default="")
    if overrides['ip']:
        overrides['gateway'] = Prompt.ask("  Gateway", default="10.10.10.1")
    
    overrides['mac'] = Prompt.ask("Custom MAC address", default="")
    overrides['hostname'] = Prompt.ask("Hostname Override", default="")

    # Build and show command
    cmd_parts = [f"python3 manage.py {i_command} {i_profile} {i_id}"]
    for k, v in overrides.items():
        if v: cmd_parts.append(f"--{k} {v}")
    
    full_cmd = " ".join(cmd_parts)
    console.print(f"\n[bold green]Constructed Command:[/bold green] [cyan]{full_cmd}[/cyan]")
    console.print("-" * 40)
    
    if Confirm.ask("Execute now?"):
        # Map interactive command to Typer function
        func_map = {
            "all": all, "deploy": deploy, "config": config,
            "test": test, "lint": lint, "build": build
        }
        
        # We need to filter overrides to only those accepted by the function
        import inspect
        target_func = func_map[i_command]
        sig = inspect.signature(target_func)
        valid_args = {k: v for k, v in overrides.items() if k in sig.parameters}
        
        # Add required positionals
        if "profile" in sig.parameters: valid_args["profile"] = i_profile
        if "id" in sig.parameters: valid_args["id"] = i_id
        
        target_func(**valid_args)
        console.print(f"\n[bold green]Execution Summary:[/bold green] {full_cmd}")
    sys.exit(0)

if __name__ == "__main__":
    load_vault()
    os.environ["VMWARE_HOST"] = os.environ.get("VCENTER_SERVER", "")
    os.environ["VMWARE_USER"] = os.environ.get("VCENTER_USERNAME", "")
    os.environ["VMWARE_PASSWORD"] = os.environ.get("VCENTER_PASSWORD", "")
    os.environ["VMWARE_VALIDATE_CERTS"] = "no"

    if len(sys.argv) == 1:
        interactive_mode()
    else:
        app()
