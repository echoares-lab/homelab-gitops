#!/usr/bin/env python3
import os
import sys
import csv
import json
import subprocess
import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table
from typing import Optional

app = typer.Typer(help="Technitium DNS OpenTofu Helper")
console = Console()

DNS_DIR = "tofu/dns"
TFVARS_FILE = f"{DNS_DIR}/terraform.tfvars"
JSON_CONFIG_FILE = f"{DNS_DIR}/records.tf.json"

@app.command()
def setup_secrets(
    host: str = typer.Option("http://10.10.10.2:5380/", "--host", help="Technitium Server URL"),
    token: str = typer.Option("[REDACTED]", "--token", help="API Token")
):
    """Interactively setup and save Technitium secrets."""
    console.print(Panel("Technitium Secrets Setup", style="bold blue"))
    
    final_host = typer.prompt("Server URL", default=host)
    final_token = typer.prompt("API Token", default=token)

    with open(TFVARS_FILE, "w") as f:
        f.write(f'technitium_host = "{final_host}"\n')
        f.write(f'technitium_token = "{final_token}"\n')
    
    console.print(f"[bold green]Secrets saved to {TFVARS_FILE}[/bold green]")

@app.command()
def convert_csv(
    csv_file: str = typer.Argument(..., help="Path to the CSV file"),
    output_json: str = typer.Option(JSON_CONFIG_FILE, "--output", help="Path to output JSON config")
):
    """Convert a DNS records CSV to OpenTofu JSON configuration."""
    if not os.path.exists(csv_file):
        console.print(f"[bold red]Error:[/bold red] CSV file '{csv_file}' not found.")
        sys.exit(1)

    records = []
    with open(csv_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            records.append(row)

    # Transform to OpenTofu JSON format
    # { "resource": { "technitium_dns_zone": { ... }, "technitium_dns_zone_record": { ... } } }
    tf_records = {}
    tf_zones = {}
    unique_zones = set()
    
    for i, row in enumerate(records):
        zone = row.get("zone")
        domain = row.get("domain")
        rtype = row.get("type", "A").upper()
        data = row.get("data")
        ttl = int(row.get("ttl", 3600))
        comments = row.get("comments", "")

        if not all([zone, domain, data]):
            console.print(f"[yellow]Skipping incomplete row {i+2}: {row}[/yellow]")
            continue

        unique_zones.add(zone)

        # Create a unique record resource name
        safe_domain = domain.replace(".", "_").replace("-", "_")
        res_name = f"rec_{safe_domain}_{rtype}_{i}"

        res_config = {
            "zone": zone,
            "domain": domain,
            "type": rtype,
            "ttl": ttl,
            "comments": comments
        }

        if rtype in ["A", "AAAA"]:
            res_config["ip_address"] = data
        elif rtype == "CNAME":
            res_config["cname"] = data
        elif rtype == "TXT":
            res_config["text"] = data
        else:
            res_config["data"] = data

        tf_records[res_name] = res_config

    for zone in unique_zones:
        safe_zone = zone.replace(".", "_").replace("-", "_")
        tf_zones[f"zone_{safe_zone}"] = {
            "name": zone,
            "type": "Primary"
        }

    tf_json = {
        "resource": {
            "technitium_dns_zone": tf_zones,
            "technitium_dns_zone_record": tf_records
        }
    }

    with open(output_json, "w") as f:
        json.dump(tf_json, f, indent=2)

    console.print(f"[bold green]Converted {len(tf_records)} records to {output_json}[/bold green]")

@app.command()
def add_record(
    csv_file: str = typer.Option("config/dns_records.csv", "--csv", help="Path to DNS records CSV")
):
    """Interactively add a new DNS record to the CSV file."""
    console.print(Panel("Interactive DNS Record Adder", style="bold blue"))
    console.print("[dim]Use this form to add a new record with detailed guidance.[/dim]\n")

    # 1. Zone
    console.print("[bold cyan]1. Authoritative Zone[/bold cyan]")
    console.print("The root domain that will hold this record.")
    console.print("Example: [green]plexplease.com[/green]\n")
    zone = Prompt.ask("Enter Zone Name")

    # 2. Domain (FQDN)
    console.print("\n[bold cyan]2. Fully Qualified Domain Name (FQDN)[/bold cyan]")
    console.print("The full name of the host you are defining.")
    console.print(f"Example: [green]www.{zone}[/green] or [green]app-01.{zone}[/green]\n")
    domain = Prompt.ask("Enter Record Domain")

    # 3. Record Type
    console.print("\n[bold cyan]3. Record Type[/bold cyan]")
    console.print("[yellow]A:[/yellow] Maps a name to an IPv4 address.")
    console.print("[yellow]AAAA:[/yellow] Maps a name to an IPv6 address.")
    console.print("[yellow]CNAME:[/yellow] Alias one name to another domain name.")
    console.print("[yellow]TXT:[/yellow] Arbitrary text (SPF, DKIM, site verification).\n")
    rtype = Prompt.ask("Select Type", choices=["A", "AAAA", "CNAME", "TXT", "MX", "SRV"], default="A")

    # 4. Record Data
    console.print(f"\n[bold cyan]4. Record Data ({rtype})[/bold cyan]")
    if rtype in ["A", "AAAA"]:
        console.print("Enter the destination IP address.")
        console.print("Example: [green]10.10.10.50[/green]\n")
    elif rtype == "CNAME":
        console.print("Enter the target domain this alias points to.")
        console.print("Example: [green]lb-prod.plexplease.com[/green]\n")
    elif rtype == "TXT":
        console.print("Enter the text content.")
        console.print("Example: [green]v=spf1 include:_spf.google.com ~all[/green]\n")
    
    data = Prompt.ask(f"Enter {rtype} Value")

    # 5. TTL
    console.print("\n[bold cyan]5. Time To Live (TTL)[/bold cyan]")
    console.print("Duration in seconds that resolvers should cache this record.")
    console.print("Default: [green]3600[/green] (1 hour). Use [green]300[/green] for fast changes.\n")
    ttl = Prompt.ask("Enter TTL", default="3600")

    # 6. Comments
    console.print("\n[bold cyan]6. Description (Optional)[/bold cyan]")
    comments = Prompt.ask("Enter a comment for this record", default="")

    # Ensure directory and file exists
    os.makedirs(os.path.dirname(csv_file), exist_ok=True)
    file_exists = os.path.isfile(csv_file)

    with open(csv_file, mode='a', newline='', encoding='utf-8') as f:
        writer = csv.writer(f)
        if not file_exists:
            writer.writerow(["zone", "domain", "type", "data", "ttl", "comments"])
        writer.writerow([zone, domain, rtype, data, ttl, comments])

    console.print(f"\n[bold green]Success![/bold green] Record for [cyan]{domain}[/cyan] added to {csv_file}")

@app.command()
def apply():
    """Initialize and apply the OpenTofu configuration."""
    console.print(Panel("Applying DNS Configuration", style="bold green"))
    
    if not os.path.exists(TFVARS_FILE):
        console.print("[bold yellow]Warning:[/bold yellow] secrets not found. Running setup first.")
        setup_secrets()

    # Tofu Init
    res = subprocess.run(["tofu", "init"], cwd=DNS_DIR)
    if res.returncode != 0:
        console.print("[bold red]Init failed.[/bold red]")
        sys.exit(1)

    # Tofu Apply
    res = subprocess.run(["tofu", "apply", "-auto-approve"], cwd=DNS_DIR)
    if res.returncode != 0:
        console.print("[bold red]Apply failed.[/bold red]")
        sys.exit(1)

    console.print("[bold green]DNS Configuration applied successfully![/bold green]")

if __name__ == "__main__":
    app()
