#!/usr/bin/env python3
import os
import sys
import csv
import json
import subprocess
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.table import Table
from typing import Optional, List, Dict, Any

app = typer.Typer(help="Advanced Technitium DNS & DHCP OpenTofu Manager", add_completion=False)
console = Console()

# --- CONFIGURATION ---
DNS_DIR = "tofu/dns"
TFVARS_FILE = f"{DNS_DIR}/terraform.tfvars"
JSON_CONFIG_FILE = f"{DNS_DIR}/records.tf.json"
CSV_FILE = "config/dns_records.csv"

# Universal CSV Headers
CSV_HEADERS = [
    "resource_type", "name", "parent", "type", "value", "ttl", 
    "mac_address", "network_address", "subnet_mask", 
    "start_address", "end_address", "gateway", 
    "comments", "depends_on", "advanced_json"
]

# Resource type help metadata
METADATA = {
    "zone": {
        "desc": "Authoritative DNS Zone",
        "fields": {
            "name": "Domain name (e.g., example.com)",
            "type": "Primary, Secondary, Forwarder, Stub",
            "value": "Forwarder IP (Required if type is Forwarder)",
        }
    },
    "record": {
        "desc": "DNS Zone Record (A, CNAME, TXT, etc.)",
        "fields": {
            "name": "Subdomain or FQDN (e.g., www.example.com)",
            "parent": "The Zone name this record belongs to",
            "type": "A, AAAA, CNAME, TXT, MX, SRV",
            "value": "IP address or target data",
        }
    },
    "dhcp_scope": {
        "desc": "DHCP IP Range Assignment",
        "fields": {
            "name": "Scope Name (e.g., Main LAN)",
            "network_address": "Network (e.g., 192.168.1.0)",
            "subnet_mask": "Mask (e.g., 255.255.255.0)",
            "start_address": "Pool Start (e.g., 192.168.1.100)",
            "end_address": "Pool End (e.g., 192.168.1.200)",
        }
    },
    "dhcp_lease": {
        "desc": "Static DHCP Reservation",
        "fields": {
            "name": "Client Hostname (optional)",
            "parent": "The Scope name or network address",
            "value": "Reserved IP Address",
            "mac_address": "Client MAC (e.g., AA:BB:CC:DD:EE:FF)",
        }
    }
}

# --- HELPER FUNCTIONS ---

def get_csv_rows() -> List[Dict[str, str]]:
    if not os.path.exists(CSV_FILE):
        return []
    with open(CSV_FILE, mode='r', encoding='utf-8') as f:
        return list(csv.DictReader(f))

def save_csv_row(row_dict: Dict[str, str]):
    os.makedirs(os.path.dirname(CSV_FILE), exist_ok=True)
    file_exists = os.path.isfile(CSV_FILE)
    
    with open(CSV_FILE, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.DictWriter(f, fieldnames=CSV_HEADERS)
        if not file_exists:
            writer.writeheader()
        writer.writerow(row_dict)

def safe_res_name(name: str) -> str:
    return name.replace(".", "_").replace("-", "_").replace(" ", "_").lower()

# --- COMMANDS ---

@app.command()
def setup_secrets(
    host: Optional[str] = typer.Option(None, "--host", help="Technitium Server URL"),
    token: Optional[str] = typer.Option(None, "--token", help="API Token")
):
    """Interactively setup and save Technitium secrets."""
    console.print(Panel("Technitium Secrets Setup", style="bold blue"))
    
    default_host = host or "http://10.10.10.2:5380/"
    default_token = token or "[REDACTED]"

    final_host = Prompt.ask("Server URL", default=default_host)
    final_token = Prompt.ask("API Token", default=default_token)

    os.makedirs(DNS_DIR, exist_ok=True)
    with open(TFVARS_FILE, "w") as f:
        f.write(f'technitium_host = "{final_host}"\n')
        f.write(f'technitium_token = "{final_token}"\n')
    console.print(f"[bold green]Secrets saved to {TFVARS_FILE}[/bold green]")

@app.command()
def add_resource():
    """Interactive wizard to add any Technitium resource to the CSV."""
    console.print(Panel("Technitium Resource Wizard", style="bold magenta"))
    
    # Select Resource Type
    r_type = Prompt.ask(
        "What would you like to add?", 
        choices=["zone", "record", "dhcp_scope", "dhcp_lease"],
        default="record"
    )
    
    data = {h: "" for h in CSV_HEADERS}
    data["resource_type"] = r_type
    
    meta = METADATA[r_type]
    console.print(f"\n[bold cyan]Adding {meta['desc']}[/bold cyan]")
    
    # Required Fields
    for field, help_text in meta["fields"].items():
        data[field] = Prompt.ask(f"{field.replace('_', ' ').title()} [dim]({help_text})[/dim]")

    # Optional Fields
    if Confirm.ask("\nConfigure optional fields (TTL, Comments, depends_on, etc.)?"):
        if r_type == "record":
            data["ttl"] = Prompt.ask("TTL (seconds)", default="3600")
        
        if r_type == "dhcp_scope":
            data["gateway"] = Prompt.ask("Default Gateway", default="")
            
        data["comments"] = Prompt.ask("Comments / Description", default="")
        dep = Prompt.ask("Depends On (comma-separated resource names, e.g. technitium_dns_zone.my_zone)", default="")
        if dep:
            data["depends_on"] = dep

    save_csv_row(data)
    console.print(f"\n[bold green]Success![/bold green] Resource added to {CSV_FILE}")

@app.command()
def convert_csv(
    csv_input: Optional[str] = typer.Option(None, "--csv", help="Path to input CSV"),
    output_json: Optional[str] = typer.Option(None, "--output", help="Path to output JSON")
):
    """Convert the Universal CSV to OpenTofu JSON configuration."""
    input_path = csv_input or CSV_FILE
    output_path = output_json or JSON_CONFIG_FILE

    if not os.path.exists(input_path):
        console.print(f"[bold red]Error:[/bold red] CSV file '{input_path}' not found.")
        if not csv_input: # If we're in interactive mode or using default, don't just exit sys
             return
        sys.exit(1)

    rows = []
    with open(input_path, mode='r', encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    tf_json = {"resource": {}}
    
    # Initialize resource buckets
    res_map = {
        "zone": "technitium_dns_zone",
        "record": "technitium_dns_zone_record",
        "dhcp_scope": "technitium_dhcp_scope",
        "dhcp_lease": "technitium_dhcp_reserved_lease"
    }
    
    for r_key in res_map.values():
        tf_json["resource"][r_key] = {}

    for i, row in enumerate(rows):
        r_type = row.get("resource_type")
        if r_type not in res_map:
            console.print(f"[yellow]Skipping unknown resource type at row {i+2}: {r_type}[/yellow]")
            continue

        res_type_name = res_map[r_type]
        name = row.get("name")
        res_id = safe_res_name(f"{r_type}_{name or i}")
        
        # Build resource object
        res_obj = {}
        
        # Mapping logic
        if r_type == "zone":
            res_obj["name"] = row["name"]
            res_obj["type"] = row["type"] or "Primary"
            if row["value"]: res_obj["forwarder"] = row["value"]
            
        elif r_type == "record":
            res_obj["zone"] = row["parent"]
            res_obj["domain"] = row["name"]
            res_obj["type"] = row["type"] or "A"
            rtype = res_obj["type"].upper()
            if rtype in ["A", "AAAA"]: res_obj["ip_address"] = row["value"]
            elif rtype == "CNAME": res_obj["cname"] = row["value"]
            elif rtype == "TXT": res_obj["text"] = row["value"]
            else: res_obj["data"] = row["value"]
            if row["ttl"]: res_obj["ttl"] = int(row["ttl"])

        elif r_type == "dhcp_scope":
            res_obj["name"] = row["name"]
            res_obj["network_address"] = row["network_address"]
            res_obj["subnet_mask"] = row["subnet_mask"]
            res_obj["start_address"] = row["start_address"]
            res_obj["end_address"] = row["end_address"]
            if row["gateway"]: res_obj["gateway"] = row["gateway"]

        elif r_type == "dhcp_lease":
            res_obj["scope"] = row["parent"]
            res_obj["ip_address"] = row["value"]
            res_obj["mac_address"] = row["mac_address"]
            if row["name"]: res_obj["host_name"] = row["name"]

        # Universal fields
        if row.get("comments"): res_obj["comments"] = row["comments"]
        if row.get("depends_on"):
            res_obj["depends_on"] = [d.strip() for d in row["depends_on"].split(",")]
            
        # Advanced JSON override
        if row.get("advanced_json"):
            try:
                overrides = json.loads(row["advanced_json"])
                res_obj.update(overrides)
            except Exception as e:
                console.print(f"[red]Error parsing advanced_json at row {i+2}: {e}[/red]")

        tf_json["resource"][res_type_name][res_id] = res_obj

    # Clean up empty resource types
    tf_json["resource"] = {k: v for k, v in tf_json["resource"].items() if v}

    with open(output_path, "w") as f:
        json.dump(tf_json, f, indent=2)

    console.print(f"[bold green]Converted {len(rows)} rows to {output_path}[/bold green]")


@app.command()
def apply():
    """Initialize and apply the OpenTofu configuration."""
    console.print(Panel("Applying Technitium Configuration", style="bold green"))
    if not os.path.exists(TFVARS_FILE):
        setup_secrets()

    subprocess.run(["tofu", "init"], cwd=DNS_DIR, check=True)
    subprocess.run(["tofu", "apply", "-auto-approve"], cwd=DNS_DIR, check=True)
    console.print("[bold green]Technitium Configuration applied successfully![/bold green]")

@app.callback(invoke_without_command=True)
def main(ctx: typer.Context):
    """
    Advanced Technitium DNS & DHCP OpenTofu Manager.
    Run without arguments to enter interactive mode.
    """
    if ctx.invoked_subcommand is None:
        interactive_menu()

def interactive_menu():
    """Interactive loop for the Technitium Manager."""
    while True:
        console.clear()
        console.print(Panel("Technitium DNS & DHCP Manager", style="bold blue"))
        
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("#", style="dim", width=3)
        table.add_column("Command", style="cyan")
        table.add_column("Description")

        commands = [
            ("1", "setup-secrets", "Configure API credentials"),
            ("2", "add-resource", "Interactive resource wizard"),
            ("3", "convert-csv", "Sync CSV to OpenTofu JSON"),
            ("4", "apply", "Run 'tofu apply'"),
            ("5", "exit", "Close the manager")
        ]

        for cmd in commands:
            table.add_row(*cmd)

        console.print(table)
        
        choice = Prompt.ask("Select an option", default="5")
        choice = choice.lower().strip()

        try:
            if choice in ["1", "setup-secrets"]:
                setup_secrets()
            elif choice in ["2", "add-resource"]:
                add_resource()
            elif choice in ["3", "convert-csv"]:
                convert_csv()
            elif choice in ["4", "apply"]:
                apply()
            elif choice in ["5", "exit", "quit", "q"]:
                console.print("[bold yellow]Goodbye![/bold yellow]")
                break
            else:
                console.print(f"[bold red]Invalid option:[/bold red] {choice}")
            
            if choice not in ["5", "exit", "quit", "q"]:
                Prompt.ask("\nPress Enter to return to menu...")
                
        except KeyboardInterrupt:
            console.print("\n[bold yellow]Exiting...[/bold yellow]")
            break
        except Exception as e:
            console.print(f"\n[bold red]Error:[/bold red] {e}")
            Prompt.ask("\nPress Enter to return to menu...")

if __name__ == "__main__":
    app()
