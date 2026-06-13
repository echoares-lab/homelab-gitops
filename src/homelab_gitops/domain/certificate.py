"""Certificate service for ACME DNS-01 workflow."""

import logging
import time
from typing import Optional, List, TYPE_CHECKING

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID

from homelab_gitops.domain.models import Task, NodeProfile

if TYPE_CHECKING:
    from homelab_gitops.drivers.acme_driver import AcmeDriver
    from homelab_gitops.drivers.technitium_driver import TechnitiumDriver
    from homelab_gitops.drivers.secrets_driver import SecretsDriver

logger = logging.getLogger(__name__)

class CertificateService:
    """Service to orchestrate ACME certificate issuance via DNS-01."""

    def __init__(
        self,
        acme_driver: "AcmeDriver",
        dns_driver: "TechnitiumDriver",
        secrets_driver: "SecretsDriver"
    ):
        """Initialize CertificateService.

        Args:
            acme_driver: Driver for ACME protocol.
            dns_driver: Driver for Technitium DNS.
            secrets_driver: Driver for 1Password secrets.
        """
        self.acme = acme_driver
        self.dns = dns_driver
        self.secrets = secrets_driver
        
        # Internal dummy profile for DNS operations
        self._dns_profile = NodeProfile(
            name="internal-ca",
            vcenter={"datacenter": "N/A", "cluster": "N/A", "datastore": "N/A", "network": "N/A"},
            vm_specs={"cpu": 1, "memory": 1, "disk": 1},
            deployment={"tags": [], "roles": [], "playbooks": []}
        )

    def issue_certificate(self, domain: str, email: str) -> str:
        """Issue a certificate for a domain using ACME DNS-01.

        Args:
            domain: Domain name to issue certificate for.
            email: Contact email for ACME account.

        Returns:
            Certificate chain in PEM format.
        """
        logger.info(f"Starting certificate issuance for {domain}")

        # 1. Generate a 2048-bit RSA private key
        logger.debug("Generating 2048-bit RSA private key")
        private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        key_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption()
        ).decode()

        # 2. Register/get ACME account
        logger.debug(f"Registering ACME account for {email}")
        self.acme.register_account(email)

        # 3. Request challenge tokens
        logger.debug(f"Requesting ACME challenges for {domain}")
        challenges = self.acme.request_challenge(domain)
        
        # 4. Update Technitium DNS with the TXT record
        # We assume the first challenge is the one we need (DNS-01)
        challenge = challenges[0]
        txt_record = challenge["txt_record"]
        validation = challenge["validation"]
        
        # Heuristic to find the zone: last two parts of the domain
        # In a real scenario, we might want to query Technitium for existing zones
        zone = ".".join(domain.split(".")[-2:])
        
        logger.info(f"Creating DNS TXT record {txt_record} in zone {zone}")
        self.dns.execute(Task(
            type="provision",
            profile=self._dns_profile,
            overrides={
                "resource": "record",
                "action": "create",
                "zone": zone,
                "domain": txt_record,
                "type": "TXT",
                "text": validation,
                "ttl": 60
            }
        ))

        try:
            # 5. Wait for DNS propagation (short sleep as requested)
            wait_time = 30
            logger.info(f"Waiting {wait_time}s for DNS propagation...")
            time.sleep(wait_time)

            # 6. Finalize ACME order
            logger.debug("Generating CSR and finalizing ACME order")
            csr = x509.CertificateSigningRequestBuilder().subject_name(x509.Name([
                x509.NameAttribute(NameOID.COMMON_NAME, domain),
            ])).add_extension(
                x509.SubjectAlternativeName([x509.DNSName(domain)]),
                critical=False,
            ).sign(private_key, hashes.SHA256())
            
            csr_pem = csr.public_bytes(serialization.Encoding.PEM).decode()
            
            cert_chain_pem = self.acme.finalize_order(domain, csr_pem)
            logger.info(f"Successfully obtained certificate for {domain}")

            # 7. Store Key + Cert in 1Password
            logger.info(f"Storing certificate and key for {domain} in 1Password")
            self.secrets.store_secret(f"cert-{domain}-key", key_pem)
            self.secrets.store_secret(f"cert-{domain}-chain", cert_chain_pem)
            
            return cert_chain_pem

        finally:
            # 8. Cleanup Technitium DNS record
            logger.info(f"Cleaning up DNS TXT record {txt_record}")
            try:
                self.dns.execute(Task(
                    type="destroy",
                    profile=self._dns_profile,
                    overrides={
                        "resource": "record",
                        "action": "delete",
                        "zone": zone,
                        "domain": txt_record,
                        "type": "TXT",
                        "text": validation
                    }
                ))
            except Exception as e:
                logger.warning(f"Failed to cleanup DNS record: {str(e)}")
