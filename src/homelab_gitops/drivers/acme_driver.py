"""ACME protocol driver for certificate management."""

import os
import time
import logging
from typing import Optional, List, Dict, Any

from acme import client, messages, crypto_util
from acme.client import ClientV2
import josepy as jose
from cryptography import x509
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa

from homelab_gitops.drivers.base import Driver
from homelab_gitops.drivers.exceptions import PrerequisiteError, ExecutionError
from homelab_gitops.domain.models import Task, TaskResult

logger = logging.getLogger(__name__)

# Default to Let's Encrypt Staging for safety
DEFAULT_DIRECTORY_URL = "https://acme-staging-v02.api.letsencrypt.org/directory"

class AcmeDriver(Driver):
    """Driver for ACME protocol operations (Metal)."""

    def __init__(
        self, 
        directory_url: Optional[str] = None, 
        account_key_pem: Optional[str] = None
    ):
        """Initialize ACME driver.
        
        Args:
            directory_url: ACME directory URL.
            account_key_pem: PEM encoded RSA private key for the ACME account.
        """
        self.directory_url = directory_url or os.getenv(
            "ACME_DIRECTORY_URL", DEFAULT_DIRECTORY_URL
        )
        self.account_key_pem = account_key_pem or os.getenv("ACME_ACCOUNT_KEY")
        self._client = None
        self._account_key = None

    def _get_client(self) -> ClientV2:
        """Lazy initialize and return ACME client."""
        if self._client:
            return self._client

        try:
            if not self.account_key_pem:
                logger.info("No ACME account key provided, generating new 2048-bit RSA key")
                # Generate a new key if none provided
                private_key = rsa.generate_private_key(
                    public_exponent=65537,
                    key_size=2048
                )
                self._account_key = jose.JWKRSA(key=private_key)
            else:
                logger.debug("Loading existing ACME account key")
                # Try loading as PEM first, then fallback to jose load
                try:
                    private_key = serialization.load_pem_private_key(
                        self.account_key_pem.encode(),
                        password=None
                    )
                    self._account_key = jose.JWKRSA(key=private_key)
                except Exception:
                    # Fallback to josepy's own loader (might be JWK JSON)
                    self._account_key = jose.JWK.load(self.account_key_pem.encode())

            logger.debug(f"Connecting to ACME directory: {self.directory_url}")
            net = client.ClientNetwork(self._account_key, user_agent="homelab-gitops/0.1.0")
            directory = client.ClientV2.get_directory(self.directory_url, net)
            self._client = client.ClientV2(directory, net)
            return self._client
        except Exception as e:
            raise PrerequisiteError(f"Failed to initialize ACME client: {str(e)}")

    def validate(self) -> bool:
        """Validate ACME directory is reachable."""
        try:
            self._get_client()
            return True
        except Exception as e:
            raise PrerequisiteError(f"ACME driver validation failed: {str(e)}")

    def register_account(self, email: str) -> str:
        """Register a new ACME account or return existing one.
        
        Args:
            email: Contact email for the account.
            
        Returns:
            Account key in PEM format.
        """
        acme_client = self._get_client()
        
        # Create registration with email
        contacts = [f"mailto:{email}"]
        regr = messages.NewRegistration.from_data(
            contact=contacts,
            terms_of_service_agreed=True
        )
        
        try:
            # Try to create new account, or return existing if key matches
            acme_client.new_account(regr)
            logger.info(f"Successfully registered/retrieved ACME account for {email}")
            
            # Return the key so it can be saved
            return self._account_key.key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            ).decode()
        except Exception as e:
            raise ExecutionError(f"Failed to register ACME account: {str(e)}")

    def request_challenge(self, domain: str) -> List[Dict[str, str]]:
        """Start DNS-01 challenge order.
        
        Args:
            domain: Domain name to request certificate for.
            
        Returns:
            List of challenge info (domain, token, txt_record).
        """
        acme_client = self._get_client()
        
        try:
            identifiers = [messages.Identifier(ty=messages.IDENTIFIER_FQDN, value=domain)]
            order = acme_client.new_order(identifiers)
            challenges = []
            
            for authz in order.authorizations:
                for challb in authz.body.challenges:
                    if isinstance(challb.chall, messages.DNS01):
                        # Calculate TXT record value
                        # The acme library provides a way to get the response
                        _, validation = challb.response_and_validation(self._account_key)
                        
                        challenges.append({
                            "domain": domain,
                            "token": challb.chall.token,
                            "txt_record": f"_acme-challenge.{domain}",
                            "validation": validation,
                        })
            
            if not challenges:
                raise ExecutionError(f"No DNS-01 challenge found for domain {domain}")
                
            return challenges
        except Exception as e:
            raise ExecutionError(f"Failed to request ACME challenge for {domain}: {str(e)}")

    def finalize_order(self, domain: str, csr_pem: str) -> str:
        """Submit CSR and download certificate.
        
        This method assumes DNS challenges have been placed. It will:
        1. Answer the challenges.
        2. Poll until the order is 'ready'.
        3. Submit the CSR.
        4. Poll until the order is 'valid'.
        5. Download and return the certificate.

        Args:
            domain: Domain name.
            csr_pem: CSR in PEM format.
            
        Returns:
            Certificate chain in PEM format.
        """
        acme_client = self._get_client()
        deadline = time.time() + 300 # 5 min timeout
        
        try:
            # Re-fetch or create the order
            identifiers = [messages.Identifier(ty=messages.IDENTIFIER_FQDN, value=domain)]
            order = acme_client.new_order(identifiers)
            
            # 1. Answer challenges if they are still pending
            for authz in order.authorizations:
                if authz.body.status == messages.STATUS_PENDING:
                    for challb in authz.body.challenges:
                        if isinstance(challb.chall, messages.DNS01):
                            acme_client.answer_challenge(challb, challb.chall.response(self._account_key))
            
            # 2. Poll for 'ready' status
            while time.time() < deadline:
                order = acme_client.poll(order)
                if order.body.status == messages.STATUS_READY:
                    break
                if order.body.status == messages.STATUS_INVALID:
                    raise ExecutionError(f"ACME order became invalid: {order.body.error}")
                time.sleep(5)
            else:
                raise ExecutionError("Timed out waiting for ACME order to be ready")
            
            # 3. Submit CSR
            csr = x509.load_pem_x509_csr(csr_pem.encode())
            order = acme_client.finalize_order(order, csr)
            
            # 4. Poll for 'valid' status
            while time.time() < deadline:
                order = acme_client.poll(order)
                if order.body.status == messages.STATUS_VALID:
                    break
                if order.body.status == messages.STATUS_INVALID:
                    raise ExecutionError(f"ACME order finalization failed: {order.body.error}")
                time.sleep(5)
            else:
                raise ExecutionError("Timed out waiting for ACME order to be valid")
            
            # 5. Download certificate
            return acme_client.fetch_chain(order)
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"Failed to finalize ACME order for {domain}: {str(e)}")

    def execute(self, task: Task) -> TaskResult:
        """Execute ACME tasks."""
        start = time.time()
        action = task.overrides.get("action", task.type)
        
        try:
            if action == "register":
                email = task.overrides.get("email")
                if not email:
                    raise ExecutionError("Email required for registration")
                output = {"account_key": self.register_account(email)}
            elif action == "challenge":
                domain = task.overrides.get("domain")
                if not domain:
                    raise ExecutionError("Domain required for challenge")
                output = {"challenges": self.request_challenge(domain)}
            elif action == "finalize":
                domain = task.overrides.get("domain")
                csr_pem = task.overrides.get("csr")
                if not domain or not csr_pem:
                    raise ExecutionError("Domain and CSR required for finalization")
                output = {"certificate": self.finalize_order(domain, csr_pem)}
            else:
                raise ExecutionError(f"Unsupported ACME action: {action}")

            return TaskResult(
                success=True,
                task_type=task.type,
                output=output,
                duration=time.time() - start
            )
        except Exception as e:
            if isinstance(e, ExecutionError):
                raise
            raise ExecutionError(f"ACME operation failed: {str(e)}")
