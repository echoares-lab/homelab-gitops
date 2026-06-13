# Certificate Management Runbook

Detailed operational procedures for managing internal SSL/TLS certificates using the GitOps Internal CA.

## Architecture Overview

The Internal CA uses the **ACME DNS-01** protocol to obtain valid certificates from Let's Encrypt without exposing internal services to the internet.

1.  **Orchestrator** (`manage.py cert`): Initiates the request.
2.  **Technitium DNS**: Hosts the temporary `_acme-challenge` TXT record for validation.
3.  **1Password Vault**: Acts as the secure repository for private keys and certificate chains.
4.  **Ansible**: Pulls certificates from 1Password and deploys them to target nodes.

---

## 1. Issuing a New Certificate

To issue a certificate for an internal service:

```bash
python3 manage.py cert issue --domain "service.mgmt.plexplease.com" --email "admin@plexplease.com"
```

### What happens under the hood:
*   A 2048-bit RSA private key is generated locally.
*   An ACME account is registered (defaults to Let's Encrypt Staging).
*   A DNS-01 challenge is requested for the domain.
*   A TXT record is created in Technitium: `_acme-challenge.service.mgmt.plexplease.com`.
*   The system waits 30 seconds for DNS propagation.
*   Let's Encrypt validates the record and issues the certificate.
*   The **Key** and **Certificate Chain** are uploaded to 1Password:
    *   Item: `cert-service.mgmt.plexplease.com-key`
    *   Item: `cert-service.mgmt.plexplease.com-chain`
*   The temporary TXT record is deleted from Technitium.

---

## 2. Deploying Certificates via Ansible

Once a certificate is in 1Password, it can be consumed by Ansible roles.

### Example Profile Integration
Add the certificate references to your node profile:

```yaml
# config/profiles/photon-docker.yml
services:
  nginx:
    ssl_cert: op://Homelab-GitOps/cert-service.mgmt.plexplease.com-chain/credential
    ssl_key: op://Homelab-GitOps/cert-service.mgmt.plexplease.com-key/credential
```

Your Ansible roles should use the `SecretsDriver` logic (via `manage.py config`) to inject these values into templates or files on the target host.

---

## 3. Environment Configuration

The ACME driver is controlled by the following environment variables (defined in `config/secrets.env` or exported manually):

| Variable | Description | Default |
| :--- | :--- | :--- |
| `ACME_DIRECTORY_URL` | Let's Encrypt API Directory | `https://acme-staging-v02.api.letsencrypt.org/directory` |
| `ACME_ACCOUNT_KEY` | Existing ACME account private key (PEM) | (Generated if missing) |

### Switching to Production
To get valid (not staging) certificates, update your `config/secrets.env`:

```env
ACME_DIRECTORY_URL=https://acme-v02.api.letsencrypt.org/directory
```

---

## 4. Troubleshooting

### DNS Propagation Timeout
If the issuance fails with "Challenge failed", the 30-second sleep might not be enough for your Technitium DNS to sync or for Let's Encrypt to see it.
*   **Check**: Verify the TXT record exists in the Technitium Web UI during the "Waiting for propagation" step.

### 1Password Permission Denied
If the "Store Key + Cert" step fails:
*   **Check**: Ensure your `OP_SERVICE_ACCOUNT_TOKEN` has **Write** access to the `Homelab-GitOps` vault.

### ACME Rate Limits
If you hit rate limits while testing:
*   **Fix**: Always use the **Staging** environment for development and testing. Staging has much higher rate limits.
