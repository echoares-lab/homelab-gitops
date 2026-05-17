#!/usr/bin/env python3
import os
import sys
import subprocess
import shutil
import time
import re
import yaml
import json
import shlex
from typing import Optional, List
from typing_extensions import Annotated

import typer
from rich.console import Console
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.panel import Panel

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

# Maps a deployment tag to its ansible playbook and any required extra-var keys.
PLAYBOOK_MAP = {
    "cf_runner":    ("cloudflare-runner.yml", ["runner_token"]),
    "cf_dev":       ("cloudflare-dev.yml",    []),
    "homelab_dev":  ("homelab-dev.yml",       []),
    "combined_dev": ("combined-dev.yml",      ["github_pat"]),
}

BUILD_TARGETS = {
    "ubuntu-2404":  ("packer/ubuntu2404.pkr.hcl", "Ubuntu 24.04 LTS"),
    "ubuntu-2604":  ("packer/ubuntu2604.pkr.hcl", "Ubuntu 26.04 LTS"),
    "photon-docker": ("packer/photon.pkr.hcl",    "VMware Photon OS"),
}

# --- HELPER FUNCTIONS ---

def _bootstrap_secrets():
    """Ensure secrets are in the environment.

    Three cases:
      1. Already loaded (called via `op run` or env pre-set) → nothing to do.
      2. OP_SERVICE_ACCOUNT_TOKEN is set → re-exec ourselves wrapped in `op run`
         so secrets from config/secrets.env are injected before the real work starts.
      3. Neither → print a helpful error and exit.
    """
    if os.environ.get("VCENTER_SERVER"):
        return  # secrets already present (op run injected them, or pre-set by caller)

    token = os.environ.get("OP_SERVICE_ACCOUNT_TOKEN")
    secrets_env = "config/secrets.env"

    if token and os.path.exists(secrets_env):
        # Re-exec this process wrapped in `op run` — the child gets all secrets injected.
        os.execvp("op", ["op", "run", f"--env-file={secrets_env}", "--", sys.executable] + sys.argv)
        # os.execvp replaces the current process; nothing below runs.

    console.print("[bold red]Error:[/bold red] Secrets not loaded.")
    if not token:
        console.print("  Set [cyan]OP_SERVICE_ACCOUNT_TOKEN[/cyan] to your service account token and re-run.")
        console.print("  [dim]Create one: 1Password → Settings → Developer → Service Accounts[/dim]")
    if not os.path.exists(secrets_env):
        console.print(f"  [yellow]Warning:[/yellow] {secrets_env} not found.")
    console.print("")
    console.print("  Or run explicitly:")
    console.print(f"    [dim]op run --env-file={secrets_env} -- python3 manage.py <command>[/dim]")
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

    env = _govc_env()
    govc_path = shutil.which("govc") or "./build/govc"

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

def resolve_playbook(profile: str) -> tuple:
    """Returns (playbook_filename, required_extra_var_keys) for a profile based on its tags."""
    profile_path = f"config/profiles/{profile}.yml"
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as f:
            c = yaml.safe_load(f)
        for tag in c.get("deployment", {}).get("tags", []):
            if tag in PLAYBOOK_MAP:
                return PLAYBOOK_MAP[tag]
    return ("site.yml", [])

def _govc_env() -> dict:
    env = os.environ.copy()
    env["GOVC_URL"] = os.environ.get("VCENTER_SERVER", "")
    env["GOVC_USERNAME"] = os.environ.get("VCENTER_USERNAME", "")
    env["GOVC_PASSWORD"] = os.environ.get("VCENTER_PASSWORD", "")
    env["GOVC_INSECURE"] = "true"
    return env

def get_host_info(hostname: str) -> dict:
    """Returns {'arch': str, 'cpu_model': str} for a host.

    Uses VMware feature capability flags (cpuid.vmx / cpuid.svm) as the
    authoritative source — these are reliable even for engineering sample
    CPUs with non-standard model strings.
    """
    govc_bin = shutil.which("govc") or "./build/govc"
    datacenter = os.environ.get("VCENTER_DATACENTER", "")
    cluster = os.environ.get("VCENTER_CLUSTER", "")
    host_path = f"/{datacenter}/host/{cluster}/{hostname}"
    res = subprocess.run(
        [govc_bin, "host.info", f"-host={host_path}", "-json"],
        capture_output=True, text=True, env=_govc_env()
    )
    try:
        data = json.loads(res.stdout)
        host_data = data["hostSystems"][0]
        hw = host_data.get("summary", {}).get("hardware", {})
        cpu_model = hw.get("cpuModel", "unknown")
        caps = {f.get("key", "") for f in host_data.get("config", {}).get("featureCapability", [])}
    except Exception:
        cpu_model = "unknown"
        caps = set()

    if "cpuid.svm" in caps:
        arch = "amd"
    elif "cpuid.vmx" in caps:
        arch = "intel"
    else:
        # Fall back to model string if caps unavailable
        model_upper = cpu_model.upper()
        if any(k in model_upper for k in ("AMD", "EPYC", "RYZEN")):
            arch = "amd"
        elif any(k in model_upper for k in ("INTEL", "XEON", "CORE", "GENUINE INTEL")):
            arch = "intel"
        else:
            arch = "unknown"

    return {"arch": arch, "cpu_model": cpu_model}

def list_cluster_hosts() -> List[str]:
    """Returns FQDNs of all ESXi hosts in the configured cluster."""
    govc_bin = shutil.which("govc") or "./build/govc"
    datacenter = os.environ.get("VCENTER_DATACENTER", "")
    cluster = os.environ.get("VCENTER_CLUSTER", "")
    res = subprocess.run(
        [govc_bin, "find", f"/{datacenter}/host/{cluster}", "-type", "h"],
        capture_output=True, text=True, env=_govc_env()
    )
    return [os.path.basename(line.strip()) for line in res.stdout.splitlines() if line.strip()]

def select_host_by_arch(preferred_arch: str) -> Optional[str]:
    """Returns the first host FQDN matching preferred_arch ('intel' or 'amd')."""
    for host in list_cluster_hosts():
        if get_host_info(host)["arch"] == preferred_arch:
            return host
    return None

def _cleanup_stale_vm(vm_name: str, target_host: str):
    """Destroy any existing VM that is not on the intended target host.

    Stale VMs left by failed deploys end up on whatever host DRS chose at
    the time.  If that host can't power the VM on (e.g. AMD-V disabled),
    every subsequent tofu apply will hit the same error.  Removing the VM
    lets tofu create it fresh on the correct host.
    """
    govc_bin = shutil.which("govc") or "./build/govc"
    datacenter = os.environ.get("VCENTER_DATACENTER", "")
    vm_path = f"/{datacenter}/vm/{vm_name}"
    env = _govc_env()

    res = subprocess.run([govc_bin, "vm.info", vm_path], capture_output=True, text=True, env=env)
    if res.returncode != 0 or not res.stdout.strip():
        return  # VM doesn't exist — nothing to clean up

    current_host = ""
    for line in res.stdout.splitlines():
        if line.strip().startswith("Host:"):
            current_host = line.split(":", 1)[1].strip()
            break

    if current_host == target_host:
        return  # VM already on the right host — let tofu handle it

    console.print(
        f"[yellow]Stale VM detected:[/yellow] '{vm_name}' exists on [bold]{current_host}[/bold] "
        f"but target host is [bold]{target_host}[/bold]."
    )
    if not Confirm.ask(f"[bold red]Destroy stale VM '{vm_name}' on {current_host} before deploying?[/bold red]"):
        console.print("[yellow]Aborted. Remove the stale VM manually or choose a different hostname.[/yellow]")
        sys.exit(1)
    subprocess.run([govc_bin, "vm.destroy", vm_path], env=env)
    console.print(f"[green]Stale VM removed.[/green]")

def run_cmd(cmd, cwd=None, capture=False):
    """Executes a shell command via subprocess safely."""
    if isinstance(cmd, str):
        cmd = shlex.split(cmd)
    res = subprocess.run(cmd, shell=False, cwd=cwd, text=True, capture_output=capture)
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
            govc_bin = shutil.which("govc") or "./build/govc"
            govc_cmd = f"{govc_bin} find . -type m -guest.ipAddress '{target}'"
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
        if hostname.endswith(f".{vm_domain}") or "." in hostname:
            vm_name = hostname
        else:
            vm_name = f"{hostname}.{vm_domain}"
    else:
        vm_name = f"{vm_prefix}-{id}.{vm_domain}"
    
    os.environ["TF_VAR_vm_name"] = vm_name
    return vm_name, c["deployment"].get("tags", [])

# --- CLI COMMANDS ---

@app.command()
def build(
    profile: Annotated[str, typer.Argument(
        help="Packer build target: [cyan]ubuntu-2404[/cyan] | [cyan]ubuntu-2604[/cyan] | [cyan]photon-docker[/cyan]"
    )] = "photon-docker"
):
    """[blue]Packer:[/blue] Build a fresh Golden OVF template from ISO.

    Targets:
      ubuntu-2404    Ubuntu 24.04 LTS  (packer/ubuntu2404.pkr.hcl)
      ubuntu-2606    Ubuntu 26.06 LTS  (packer/ubuntu2606.pkr.hcl)
      photon-docker  VMware Photon OS  (packer/photon.pkr.hcl)

    Requires vault keys: VCENTER_*, SSH_ADMIN_*, and the matching ISO_URL / ISO_CHECKSUM.
    """
    start = time.time()
    console.print(Panel(f"Building Golden OVF Template via Packer ({profile})", style="blue"))

    vcenter_base = {
        "vcenter_server": "VCENTER_SERVER",
        "vcenter_username": "VCENTER_USERNAME",
        "vcenter_password": "VCENTER_PASSWORD",
        "datacenter": "VCENTER_DATACENTER",
        "cluster": "VCENTER_CLUSTER",
        "datastore": "VCENTER_DATASTORE",
        "network": "VCENTER_NETWORK",
    }

    if "ubuntu-2404" in profile or profile == "ubuntu2404":
        packer_file = "packer/ubuntu2404.pkr.hcl"
        env_map = {
            **vcenter_base,
            "ubuntu_iso_url": "UBUNTU_2404_ISO_URL",
            "ubuntu_iso_checksum": "UBUNTU_2404_ISO_CHECKSUM",
            "ssh_username": "SSH_ADMIN_USERNAME",
            "ssh_password": "SSH_ADMIN_PASSWORD",
        }
    elif "ubuntu-2604" in profile or profile == "ubuntu2604":
        packer_file = "packer/ubuntu2604.pkr.hcl"
        env_map = {
            **vcenter_base,
            "ubuntu_iso_url": "UBUNTU_2604_ISO_URL",
            "ubuntu_iso_checksum": "UBUNTU_2604_ISO_CHECKSUM",
            "ssh_username": "SSH_ADMIN_USERNAME",
            "ssh_password": "SSH_ADMIN_PASSWORD",
        }
    else:
        packer_file = "packer/photon.pkr.hcl"
        env_map = {
            "vcenter_server": "VCENTER_SERVER",
            "vcenter_username": "VCENTER_USERNAME",
            "vcenter_password": "VCENTER_PASSWORD",
            "datacenter": "VCENTER_DATACENTER",
            "cluster": "VCENTER_CLUSTER",
            "datastore": "VCENTER_DATASTORE",
            "network": "VCENTER_NETWORK",
            "photon_iso_url": "PHOTON_ISO_URL",
            "photon_iso_checksum": "PHOTON_ISO_CHECKSUM",
            "ssh_username": "SSH_ADMIN_USERNAME",
            "ssh_password": "SSH_ADMIN_PASSWORD",
        }

    for packer_var, env_var in env_map.items():
        os.environ[f"PKR_VAR_{packer_var}"] = os.environ.get(env_var, "")

    run_cmd(f"packer init {packer_file}")
    run_cmd(f"packer build {packer_file}")
    track_time(start, "Packer Build")

@app.command(name="bu")
def bu(
    profile: Annotated[str, typer.Argument(
        help="Packer build target: ubuntu-2404 | ubuntu-2604 | photon-docker"
    )] = "photon-docker"
):
    """[blue]Packer:[/blue] Alias for [cyan]build[/cyan]."""
    build(profile)

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
    host: Annotated[str, typer.Option(help="Override target host (or 'auto')")] = "auto",
    cpu_arch: Annotated[str, typer.Option(help="Preferred CPU arch: intel or amd")] = "intel",
    mac: Annotated[str, typer.Option(help="Override MAC")] = "",
    ip: Annotated[str, typer.Option(help="Set static IP")] = "",
    hostname: Annotated[str, typer.Option(help="Override hostname")] = "",
    netmask: Annotated[str, typer.Option(help="Subnet bits")] = "24",
    gateway: Annotated[str, typer.Option(help="Default gateway")] = "",
    dns: Annotated[str, typer.Option(help="Primary DNS")] = "10.10.10.2"
):
    """[blue]Provision:[/blue] Deploy virtual hardware via OpenTofu."""
    start = time.time()
    console.print(Panel(f"Unified OpenTofu Deployment ({profile})", style="blue"))

    # Resolve target host
    if host == "auto":
        with console.status(f"[bold blue]Scanning cluster for {cpu_arch.upper()} host..."):
            host = select_host_by_arch(cpu_arch)
        if not host:
            console.print(f"[bold red]Error:[/bold red] No {cpu_arch.upper()} host found in cluster.")
            sys.exit(1)
        console.print(f"[green]Auto-selected host:[/green] {host}")
    else:
        with console.status(f"[bold blue]Checking CPU architecture of {host}..."):
            host_info = get_host_info(host)
        detected_arch = host_info["arch"]
        cpu_model = host_info["cpu_model"]
        arch_color = "green" if detected_arch == cpu_arch else "yellow"
        console.print(f"[{arch_color}]Host CPU:[/{arch_color}] {host} → {detected_arch.upper()} ({cpu_model})")
        if detected_arch != cpu_arch and detected_arch != "unknown":
            console.print(
                f"[yellow]Warning:[/yellow] {host} is {detected_arch.upper()} but --cpu-arch={cpu_arch}. "
                f"Use --cpu-arch={detected_arch} or --host=auto to avoid compatibility issues."
            )

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

    _cleanup_stale_vm(vm_name, host)

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
    profile: Annotated[str, typer.Argument(
        help="Profile name (e.g. ubuntu-2404-cf-dev). Playbook is auto-selected from the profile's tags."
    )] = "photon-docker",
    id: Annotated[Optional[str], typer.Argument(help="Instance ID — limits run to that specific VM")] = None,
    hostname: Annotated[str, typer.Option(
        help="Explicit hostname/IP to target instead of the tag group"
    )] = "",
    extra_vars: Annotated[str, typer.Option(
        "--extra-vars", "-e",
        help="Additional Ansible vars (e.g. 'runner_token=abc' or 'github_pat=xyz')"
    )] = "",
):
    """[blue]Configure:[/blue] Apply Ansible roles via the profile-matched playbook.

    Playbook is selected automatically from the profile's deployment tags:
      cf_runner    → cloudflare-runner.yml  (requires runner_token)
      cf_dev       → cloudflare-dev.yml
      homelab_dev  → homelab-dev.yml
      combined_dev → combined-dev.yml       (requires github_pat)
      (other)      → site.yml

    SSH_ADMIN_SSH_PUBKEY from vault is forwarded automatically as ansible_admin_pubkey.
    """
    start = time.time()
    playbook, required_vars = resolve_playbook(profile)
    console.print(Panel(
        f"Ansible Configuration  •  profile=[cyan]{profile}[/cyan]  •  playbook=[yellow]{playbook}[/yellow]",
        style="blue"
    ))

    # Warn if any required extra vars for this playbook are missing
    ev_dict_check = {}
    if extra_vars:
        for pair in extra_vars.split():
            if "=" in pair:
                k, v = pair.split("=", 1)
                ev_dict_check[k.strip()] = v.strip()
    for rv in required_vars:
        if rv not in ev_dict_check:
            console.print(f"[yellow]Warning:[/yellow] playbook [cyan]{playbook}[/cyan] typically requires [bold]-e {rv}=...[/bold]")

    # Derive profile tags for group naming
    profile_tags = []
    profile_path = f"config/profiles/{profile}.yml"
    if os.path.exists(profile_path):
        with open(profile_path, 'r') as pf:
            pc = yaml.safe_load(pf)
        profile_tags = pc.get("deployment", {}).get("tags", [])

    # When an explicit hostname/IP is given, build a temp inline inventory that
    # places the host into the expected tag groups so playbook host patterns match.
    temp_inv_path = ""
    inventory_arg = "inventory/vmware_vms.yml"
    limit_arg = ""

    if hostname:
        import tempfile
        ssh_user = os.environ.get("SSH_ADMIN_USERNAME", "ansible")
        host_entry = f"{hostname} ansible_user={ssh_user}\n"
        lines = ["[all]\n", host_entry]
        for tag in profile_tags:
            lines += [f"\n[tag_{tag}]\n", host_entry]
        tf = tempfile.NamedTemporaryFile(mode="w", suffix=".ini", delete=False)
        tf.writelines(lines)
        tf.flush()
        temp_inv_path = tf.name
        tf.close()
        inventory_arg = temp_inv_path
        limit_arg = f"-l {hostname}"
        console.print(f"[yellow]Limit:[/yellow] explicit host ({hostname})")
    elif id:
        vm_name, _ = load_profile_to_env(profile, id, "", "", "", "", "24", "", "10.10.10.2")
        limit_arg = f"-l {vm_name}"
        console.print(f"[yellow]Limit:[/yellow] instance ({vm_name})")
    else:
        if profile_tags:
            primary_tag = profile_tags[0]
            limit_arg = f"-l tag_{primary_tag}"
            console.print(f"[yellow]Limit:[/yellow] tag group (tag_{primary_tag})")
        if not limit_arg:
            console.print("[yellow]Limit:[/yellow] none (all hosts)")

    os.environ["ANSIBLE_HOST_KEY_CHECKING"] = "False"
    ssh_key = os.path.expanduser(os.environ.get("SSH_PRIVATE_KEY_PATH", ""))
    ssh_pass = os.environ.get("SSH_ADMIN_PASSWORD", "")
    pubkey = os.environ.get("SSH_ADMIN_SSH_PUBKEY", "")

    # Build extra-vars as JSON for robust quoting (handles spaces in pubkeys, tokens, etc.)
    # Prefer key auth when SSH_PRIVATE_KEY_PATH is set; fall back to password only if no key.
    ev_dict = {}
    if ssh_pass and not ssh_key:
        ev_dict["ansible_ssh_pass"] = ssh_pass
    if pubkey:
        ev_dict["ansible_admin_pubkey"] = pubkey
    if extra_vars:
        for pair in extra_vars.split():
            if "=" in pair:
                k, v = pair.split("=", 1)
                ev_dict[k.strip()] = v.strip()

    ev_json = json.dumps(ev_dict)

    ansible_cmd = (
        f"ansible-playbook -i {inventory_arg} {playbook} {limit_arg} "
        f"--private-key '{ssh_key}' "
        f"--extra-vars '{ev_json}' "
        f"--ssh-extra-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'"
    )
    try:
        run_cmd(ansible_cmd, cwd="ansible")
    finally:
        if temp_inv_path and os.path.exists(temp_inv_path):
            os.unlink(temp_inv_path)
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
    
    os.environ["RUNTIME_PROFILE"] = profile
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
    dns: Annotated[str, typer.Option(help="DNS")] = "10.10.10.2",
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

# --- ALIASES ---
# Short-form commands for every core and generator operation.
# Each is a full duplicate registration so --help, tab-complete, and
# non-interactive invocation all work identically to the canonical name.
app.command(name="li",        help="Alias for [cyan]lint[/cyan]"          )(lint)
app.command(name="dep",       help="Alias for [cyan]deploy[/cyan]"        )(deploy)
app.command(name="cfg",       help="Alias for [cyan]config[/cyan]"        )(config)
app.command(name="ts",        help="Alias for [cyan]test[/cyan]"          )(test)
app.command(name="rm",        help="Alias for [cyan]destroy[/cyan]"       )(destroy)
app.command(name="a",         help="Alias for [cyan]all[/cyan]"           )(all)
app.command(name="mkprofile", help="Alias for [cyan]create-profile[/cyan]")(create_profile)
app.command(name="ep",        help="Alias for [cyan]edit-profile[/cyan]"  )(edit_profile)
app.command(name="mkrole",    help="Alias for [cyan]create-role[/cyan]"   )(create_role)
app.command(name="mkplay",    help="Alias for [cyan]create-play[/cyan]"   )(create_play)

# --- INTERACTIVE MODE ---

def interactive_mode():
    import inspect

    # ── Helper: list existing Tofu workspaces ─────────────────────────────────────
    def _show_workspaces(title="Existing deployed workspaces"):
        try:
            res = run_cmd("tofu workspace list", cwd="tofu", capture=True)
            names = [l.replace("*", "").strip() for l in res.stdout.splitlines()
                     if l.strip() and l.strip() not in ("", "default")]
            if names:
                t = Table(show_header=False, box=None, pad_edge=False)
                t.add_column(style="dim cyan")
                for n in names:
                    t.add_row(n)
                console.print(f"\n[dim]{title}:[/dim]")
                console.print(t)
            else:
                console.print("[dim]  (no workspaces deployed yet)[/dim]")
        except Exception:
            pass

    # ── Helper: list cluster ESXi hosts with arch ─────────────────────────────────
    def _show_hosts():
        try:
            hosts = list_cluster_hosts()
            if not hosts:
                return
            t = Table(show_header=True, header_style="bold", box=None, pad_edge=False)
            t.add_column("Host",  style="cyan")
            t.add_column("Arch",  style="yellow")
            t.add_column("CPU",   style="dim")
            for h in hosts:
                info = get_host_info(h)
                t.add_row(h, info["arch"].upper(), info["cpu_model"])
            console.print("\n[dim]Available ESXi hosts in cluster:[/dim]")
            console.print(t)
            console.print("[dim]  Use 'auto' to let the orchestrator pick by arch preference.[/dim]")
        except Exception:
            console.print("[dim]  (could not reach vCenter to list hosts)[/dim]")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 1 — Command
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    console.print(Panel.fit("HomeLab GitOps Command Builder", style="bold magenta", border_style="cyan"))

    ALIASES = {
        "build":          "bu",
        "lint":           "li",
        "deploy":         "dep",
        "config":         "cfg",
        "test":           "ts",
        "destroy":        "rm",
        "all":            "a",
        "create-profile": "mkprofile",
        "edit-profile":   "ep",
        "create-role":    "mkrole",
        "create-play":    "mkplay",
    }
    CMD_NOTES = {
        "build":          "ISO → golden OVF/OVA in Content Library",
        "lint":           "validate profile YAML + vCenter objects",
        "deploy":         "provision VM via OpenTofu",
        "config":         "apply Ansible roles (playbook auto-selected by profile tag)",
        "test":           "pytest-testinfra smoke tests against the VM",
        "destroy":        "remove VM + isolated Tofu state",
        "all":            "full pipeline: lint → deploy → config → test → destroy",
        "create-profile": "scaffold a new YAML VM profile",
        "edit-profile":   "edit an existing profile interactively",
        "create-role":    "scaffold a new Ansible role skeleton",
        "create-play":    "add a targeting play to site.yml",
    }

    core_cmds = ["build", "lint", "deploy", "config", "test", "destroy", "all"]
    gen_cmds  = ["create-profile", "edit-profile", "create-role", "create-play"]

    cmd_table = Table(show_header=True, header_style="bold cyan", box=None)
    cmd_table.add_column("Command",  style="bold white",  min_width=14)
    cmd_table.add_column("Alias",    style="cyan",        min_width=10)
    cmd_table.add_column("What it does", style="italic dim")

    for c in core_cmds + gen_cmds:
        cmd_table.add_row(c, ALIASES.get(c, ""), CMD_NOTES.get(c, ""))

    console.print(cmd_table)
    console.print(
        "[dim]All commands also run non-interactively: [cyan]python3 manage.py <cmd> --help[/cyan][/dim]\n"
    )

    i_command = Prompt.ask("Select command", choices=core_cmds + gen_cmds + ["Quit"])
    if i_command == "Quit":
        sys.exit(0)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2a — Generators (no further input needed)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if i_command in gen_cmds:
        func_map = {
            "create-profile": create_profile, "edit-profile":  edit_profile,
            "create-role":    create_role,    "create-play":   create_play,
        }
        func_map[i_command]()
        sys.exit(0)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2b — Destroy
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if i_command == "destroy":
        _show_workspaces("Managed VMs you can destroy")
        console.print(
            "\n[dim]Identifier options:[/dim]\n"
            "  [cyan]VM name[/cyan]    exact or partial workspace name (e.g. cf-runner-01)\n"
            "  [cyan]IP address[/cyan] e.g. 10.10.10.55  (looked up in vCenter)\n"
            "  [cyan]MAC address[/cyan] e.g. 00:50:56:aa:bb:cc\n"
        )
        i_id = Prompt.ask("VM identifier")
        if i_id:
            destroy(identifier=i_id)
        sys.exit(0)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 2c — Build (packer targets, not deploy profiles)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    if i_command == "build":
        b_table = Table(show_header=True, header_style="bold green", box=None)
        b_table.add_column("Target",       style="bold white")
        b_table.add_column("OS",           style="cyan")
        b_table.add_column("Packer file",  style="dim")
        for target, (pfile, os_name) in BUILD_TARGETS.items():
            b_table.add_row(target, os_name, pfile)
        console.print("\nAvailable build targets:")
        console.print(b_table)
        console.print(
            "\n[dim]Vault keys required:[/dim]\n"
            "  VCENTER_SERVER / USERNAME / PASSWORD / DATACENTER / CLUSTER / DATASTORE / NETWORK\n"
            "  SSH_ADMIN_USERNAME / SSH_ADMIN_PASSWORD\n"
            "  <TARGET>_ISO_URL + <TARGET>_ISO_CHECKSUM   (e.g. UBUNTU_2404_ISO_URL)\n"
        )
        i_target = Prompt.ask("Select target", choices=list(BUILD_TARGETS.keys()))
        full_cmd = f"python3 manage.py build {i_target}"
        console.print(f"\n[bold green]Command:[/bold green] [cyan]{full_cmd}[/cyan]\n")
        if Confirm.ask("Execute now?"):
            build(i_target)
        sys.exit(0)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 3 — Profile
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    profiles = sorted(f.replace(".yml", "") for f in os.listdir("config/profiles") if f.endswith(".yml"))

    PLAYBOOK_NOTES = {
        "site.yml":               "base + security for generic ubuntu/photon hosts",
        "cloudflare-runner.yml":  "org-level GitHub Actions runner  [requires runner_token]",
        "cloudflare-dev.yml":     "cloudflare_access_automation dev tools",
        "homelab-dev.yml":        "homelab-gitops dev tools (tofu, packer, govc, ansible)",
        "combined-dev.yml":       "full dev workstation, both repos  [requires github_pat]",
    }

    p_table = Table(show_header=True, header_style="bold green", box=None)
    p_table.add_column("Profile",   style="bold white")
    p_table.add_column("Tags",      style="cyan",   min_width=20)
    p_table.add_column("Specs",     style="dim",    min_width=28)
    p_table.add_column("Playbook",  style="yellow")
    p_table.add_column("Notes",     style="italic dim")

    for p in profiles:
        with open(f"config/profiles/{p}.yml", "r") as f:
            c = yaml.safe_load(f)
        tags  = ", ".join(c["deployment"].get("tags", []))
        vs    = c["vm_specs"]
        specs = f"{vs['cpu']}vCPU / {vs['ram_gb']}GB RAM / {vs['disk_size_gb']}GB"
        pb, _ = resolve_playbook(p)
        note  = PLAYBOOK_NOTES.get(pb, "")
        p_table.add_row(p, tags, specs, pb, note)

    console.print("\nAvailable profiles:")
    console.print(p_table)
    console.print(
        "[dim]A profile sets VM hardware, vCenter placement, deployment tags, and\n"
        "which Ansible playbook is applied by [cyan]config[/cyan].[/dim]\n"
    )
    i_profile = Prompt.ask("Select profile", choices=profiles)
    i_playbook, i_required_vars = resolve_playbook(i_profile)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 4 — Instance ID
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    _show_workspaces("Already-deployed workspaces (avoid duplicating these IDs)")
    console.print(
        "\n[dim]Instance ID is appended to the profile's vm_name_prefix to form the VM name.\n"
        "  Example: prefix=[cyan]cf-runner[/cyan]  id=[cyan]01[/cyan]  → VM name [cyan]cf-runner-01.mgmt.plexplease.com[/cyan]\n"
        "  Use --hostname to set a fully custom name instead.[/dim]"
    )
    i_id = Prompt.ask("\nInstance ID", default="01")

    console.print(f"\n[dim]Playbook that will run:[/dim] [yellow]{i_playbook}[/yellow]")
    if i_playbook in PLAYBOOK_NOTES:
        console.print(f"[dim]  {PLAYBOOK_NOTES[i_playbook]}[/dim]")

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 5 — Deploy overrides  (deploy / all only)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    overrides: dict = {}

    if i_command in ("deploy", "all"):
        console.print("\n[dim]── Network & placement overrides — Enter to keep default ──[/dim]")

        # Host
        _show_hosts()
        overrides["host"] = Prompt.ask(
            "\nTarget ESXi host [dim]('auto' = orchestrator picks by arch)[/dim]",
            default="auto"
        )
        if overrides["host"] == "auto":
            console.print(
                "[dim]  Arch options:\n"
                "    intel  — picks first host with VMX (VT-x) capability\n"
                "    amd    — picks first host with SVM (AMD-V) capability[/dim]"
            )
            overrides["cpu_arch"] = Prompt.ask(
                "  Preferred CPU arch", default="intel", choices=["intel", "amd"]
            )

        # IP / network
        console.print(
            "\n[dim]  Static IP — leave blank to rely on DHCP/VM customization.\n"
            "  If set, gateway and DNS are also required.[/dim]"
        )
        overrides["ip"] = Prompt.ask(
            "Static IP [dim](e.g. 10.10.10.55)[/dim]", default=""
        )
        if overrides["ip"]:
            console.print(
                "[dim]  Common prefix lengths:\n"
                "    24 → 255.255.255.0   (254 hosts)\n"
                "    23 → 255.255.254.0   (510 hosts)\n"
                "    16 → 255.255.0.0     (65 534 hosts)[/dim]"
            )
            overrides["netmask"] = Prompt.ask(
                "  Prefix length [dim](bits)[/dim]", default="24"
            )
            overrides["gateway"] = Prompt.ask(
                "  Default gateway", default="10.10.10.1"
            )
            overrides["dns"] = Prompt.ask(
                "  Primary DNS server [dim](vault default: 10.10.10.2)[/dim]",
                default="10.10.10.2"
            )

        # MAC
        console.print(
            "\n[dim]  MAC address — blank = vCenter auto-assigns.\n"
            "  Set explicitly to keep a DHCP reservation stable across redeployments.\n"
            "  Format: xx:xx:xx:xx:xx:xx[/dim]"
        )
        overrides["mac"] = Prompt.ask(
            "MAC address [dim](blank = auto)[/dim]", default=""
        )

        # Hostname
        with open(f"config/profiles/{i_profile}.yml") as f:
            _pc = yaml.safe_load(f)
        _prefix = _pc["deployment"].get("vm_name_prefix", "node")
        _domain = _pc["deployment"].get("vm_name_domain", "local")
        console.print(
            f"\n[dim]  Hostname — blank = [cyan]{_prefix}-{i_id}.{_domain}[/cyan]\n"
            f"  Set to override with a custom FQDN or short name.[/dim]"
        )
        overrides["hostname"] = Prompt.ask(
            "Hostname override [dim](blank = auto)[/dim]", default=""
        )

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 6 — Secret extra-vars (playbook-specific)
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    ev_parts: list = []

    if "runner_token" in i_required_vars:
        console.print(
            "\n[bold yellow]Runner token required[/bold yellow]\n"
            "  [dim]1. Go to:[/dim] github.com/organizations/echoares-lab/settings/actions/runners/new\n"
            "  [dim]2. Click 'New self-hosted runner' → copy the token from the config command.[/dim]\n"
            "  [dim]3. Token expires 1 hour after generation — run this promptly.[/dim]\n"
            "  [dim]Vault key if you want to pre-store it: [cyan]runner_token[/cyan][/dim]"
        )
        tok = Prompt.ask("  Runner registration token", password=True)
        if tok:
            ev_parts.append(f"runner_token={tok}")

    if "github_pat" in i_required_vars:
        console.print(
            "\n[bold yellow]GitHub PAT required[/bold yellow]\n"
            "  [dim]1. Go to:[/dim] github.com/settings/tokens → 'Generate new token (classic)'\n"
            "  [dim]2. Required scopes: [cyan]repo[/cyan], [cyan]read:org[/cyan][/dim]\n"
            "  [dim]3. The PAT is used once to authenticate gh CLI and clone repos.[/dim]\n"
            "  [dim]Tip: store it in 1Password → Homelab-GitOps/GitHub/github_pat[/dim]"
        )
        # Try to resolve from 1Password automatically
        auto_pat = ""
        if os.environ.get("OP_SERVICE_ACCOUNT_TOKEN"):
            try:
                res = subprocess.run(
                    ["op", "read", "op://Homelab-GitOps/GitHub/github_pat"],
                    capture_output=True, text=True
                )
                if res.returncode == 0 and res.stdout.strip():
                    auto_pat = res.stdout.strip()
                    console.print("  [green]GitHub PAT loaded from 1Password automatically.[/green]")
            except FileNotFoundError:
                pass
        if auto_pat:
            ev_parts.append(f"github_pat={auto_pat}")
        else:
            pat = Prompt.ask("  GitHub Personal Access Token", password=True)
            if pat:
                ev_parts.append(f"github_pat={pat}")

    if ev_parts:
        overrides["extra_vars"] = " ".join(ev_parts)

    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    # STEP 7 — Show constructed command + execute
    # ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    cmd_parts = [f"python3 manage.py {i_command} {i_profile} {i_id}"]
    for k, v in overrides.items():
        if not v:
            continue
        if k == "extra_vars":
            cmd_parts.append(f'-e "{v}"')
        else:
            cmd_parts.append(f"--{k.replace('_', '-')} {v}")

    full_cmd = " ".join(cmd_parts)
    console.print(f"\n[bold green]Constructed command:[/bold green]\n  [cyan]{full_cmd}[/cyan]")
    console.print("[dim]  Paste this next time to skip the menu entirely.[/dim]\n")

    if Confirm.ask("Execute now?"):
        func_map = {
            "all": all, "deploy": deploy, "config": config,
            "test": test, "lint": lint,
        }
        target_func = func_map[i_command]
        sig = inspect.signature(target_func)
        valid_args = {k: v for k, v in overrides.items() if k in sig.parameters and v}
        if "profile" in sig.parameters:
            valid_args["profile"] = i_profile
        if "id" in sig.parameters:
            valid_args["id"] = i_id
        target_func(**valid_args)
        console.print("\n[bold green]Done.[/bold green]")
    sys.exit(0)

if __name__ == "__main__":
    _bootstrap_secrets()
    os.environ["VMWARE_HOST"] = os.environ.get("VCENTER_SERVER", "")
    os.environ["VMWARE_USER"] = os.environ.get("VCENTER_USERNAME", "")
    os.environ["VMWARE_PASSWORD"] = os.environ.get("VCENTER_PASSWORD", "")
    os.environ["VMWARE_VALIDATE_CERTS"] = "no"

    if len(sys.argv) == 1:
        interactive_mode()
    else:
        app()
