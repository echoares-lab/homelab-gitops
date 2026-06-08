# Observability TLS Certificate Setup

This guide covers how to generate and distribute TLS certificates for Docker daemon TLS sockets used by dockerhand and uptime-kuma.

## Prerequisites

- OPNsense router with CA configured
- Access to OPNsense WebUI or API
- Ansible control node with access to playbooks

## Step 1: Generate Certificates on OPNsense

### Via OPNsense WebUI:

1. Go to **System > Trust > Certificates**
2. Click **Add** to create a new certificate
3. Fill in:
   - **Name:** `docker-web-01` (node name)
   - **Type:** Server Certificate
   - **CA:** Select your internal CA
   - **Common Name:** `docker-web-01.mgmt.plexplease.com` (node FQDN)
4. Save
5. Export as PEM:
   - Certificate (`.crt`)
   - Key (`.key`) — keep private!
   - CA cert (if not already have)

### Naming Convention:

- `ca.crt` — CA public certificate (same for all nodes)
- `server.crt` — Node-specific server certificate
- `server.key` — Node-specific server key (sensitive)

## Step 2: Distribute Certificates via Ansible

1. Place certificates in role files:
   ```bash
   cp opnsense/ca.crt ansible/roles/docker_metrics/files/
   cp opnsense/docker-web-01.crt ansible/roles/docker_metrics/files/server.crt
   cp opnsense/docker-web-01.key ansible/roles/docker_metrics/files/server.key
   ```

2. Run site.yml to apply docker_metrics role:
   ```bash
   python3 manage.py config PROFILE INDEX
   ```

3. Verify on node:
   ```bash
   ssh user@docker-web-01 ls -la /etc/docker/certs.d/
   # Should show: ca.crt, server.crt, server.key
   ```

## Step 3: Test TLS Connection

From 10.10.10.30 or any node with Docker client:

```bash
docker -H tcp://docker-web-01.mgmt.plexplease.com:2376 \
  --tlscacert=/etc/docker/certs.d/ca.crt \
  --tlscert=/etc/docker/certs.d/client.crt \
  --tlskey=/etc/docker/certs.d/client.key \
  ps
```

Expected: List of running containers on docker-web-01.

## Certificate Renewal

1. OPNsense: Re-issue certificate (extend validity or regenerate)
2. Export new cert/key
3. Update `ansible/roles/docker_metrics/files/{server.crt,server.key}`
4. Run site.yml to distribute
5. Docker daemon auto-reloads on config change

## Troubleshooting

**Connection refused:**
- Check Docker daemon is running: `systemctl status docker`
- Check TLS port is listening: `netstat -tuln | grep 2376`

**Certificate verification failed:**
- Verify CA cert matches: Compare fingerprints between node and central
- Check cert expiry: `openssl x509 -in server.crt -noout -dates`

**Alloy can't scrape Docker metrics:**
- Verify `/var/run/docker.sock` exists: `ls -la /var/run/docker.sock`
- Check Alloy logs: `journalctl -u alloy -f`
