"""Certificate management CLI plugin."""

import typer
from typing import Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from homelab_gitops.domain.certificate import CertificateService
from homelab_gitops.drivers.acme_driver import AcmeDriver
from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
from homelab_gitops.drivers.secrets_driver import SecretsDriver

console = Console()
app = typer.Typer(help="Manage ACME certificates")


def cert_command():
    """Entry point for the cert command group."""
    return app


@app.command(name="issue")
def issue_cert(
    domain: str = typer.Option(..., "--domain", "-d", help="Domain name to issue certificate for"),
    email: str = typer.Option(..., "--email", "-e", help="Contact email for ACME account"),
    staging: bool = typer.Option(True, help="Use Let's Encrypt staging environment")
):
    """Issue a certificate for a domain using ACME DNS-01."""
    
    # Initialize drivers
    # Note: AcmeDriver defaults to staging if not specified, but we can be explicit
    directory_url = None
    if not staging:
        directory_url = "https://acme-v02.api.letsencrypt.org/directory"
    
    acme_driver = AcmeDriver(directory_url=directory_url)
    dns_driver = TechnitiumDriver()
    secrets_driver = SecretsDriver()
    
    service = CertificateService(
        acme_driver=acme_driver,
        dns_driver=dns_driver,
        secrets_driver=secrets_driver
    )
    
    console.print(f"[bold blue]Starting certificate issuance for {domain}...[/bold blue]")
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
        transient=True
    ) as progress:
        task = progress.add_task(description=f"Issuing certificate for {domain}...", total=None)
        
        try:
            service.issue_certificate(domain, email)
            progress.update(task, description=f"[green]Successfully issued certificate for {domain}[/green]")
            console.print(f"\n[bold green]Success![/bold green] Certificate for {domain} has been issued and stored in 1Password.")
        except Exception as e:
            progress.update(task, description=f"[red]Failed to issue certificate[/red]")
            console.print(f"\n[bold red]Error:[/bold red] {str(e)}")
            raise typer.Exit(code=1)


@app.command(name="status")
def cert_status():
    """Check status of certificates (Stub)."""
    console.print("[yellow]Certificate status command is not yet fully implemented.[/yellow]")
    console.print("Currently, certificates are stored in 1Password with tags.")


command_metadata = {
    "name": "cert",
    "help": "Manage ACME certificates",
    "is_app": True
}
