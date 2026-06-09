# Secrets Management Troubleshooting

Common issues and solutions.

## "Cannot connect to 1Password Connect"

**Error:** `curl: (7) Failed to connect to {connect-hostname}:8200`

**Check:**
1. Connect server is running: `docker ps | grep op-connect`
2. Network connectivity: `ping {connect-hostname}`
3. Firewall allows 8200: `telnet {connect-hostname} 8200`

**Solution:**
```bash
docker restart op-connect-api op-connect-sync
docker logs op-connect-api | tail -20
```

## "Authorization failed" or "Forbidden"

**Error:** `curl: (22) HTTP 403 Forbidden`

**Check:**
1. Token is set: `echo $OP_CONNECT_TOKEN`
2. Token is valid: `cat /etc/op-connect/token`
3. Your role has access to the vault/item
4. Token hasn't expired

**Solution:**
```bash
# Verify token format
cat /etc/op-connect/token
# Should start with "ops_"

# Regenerate if needed (see: Secrets Runbook → Rotating Connect Token)
```

## "Secret not found"

**Error:** `op read op://vault/folder/SECRET: not found`

**Check:**
1. Vault exists: `op vault list`
2. Item exists in vault: `op vault contents homelab-gitops`
3. Folder is correct (dev/, prod/, ci/)
4. Name matches exactly (case-sensitive)

**Solution:**
```bash
# List contents of vault
export OP_CONNECT_TOKEN=$(cat /etc/op-connect/token)
op run --server https://{connect-hostname}:8200 -- \
  op vault contents homelab-gitops | grep SEARCH_TERM

# Verify exact path
op run --server https://{connect-hostname}:8200 -- \
  op read op://homelab-gitops/prod/SECRET_NAME
```

## "op run: command not found"

**Error:** `bash: op: command not found`

**Check:**
1. `op` CLI is installed: `which op`
2. It's in PATH: `echo $PATH`

**Solution:**
```bash
# Install op CLI
curl https://cache.agilebits.com/dist/1P/op/pkg/v2.22.0/op_linux_amd64_v2.22.0.zip -o op.zip
unzip op.zip
sudo mv op /usr/local/bin/
op --version
```

## "Permission denied" reading token

**Error:** `cat: /etc/op-connect/token: Permission denied`

**Check:**
Token file permissions: `ls -la /etc/op-connect/token`
Expected: `-rw-r--r-- 1 root root` (644, not 600)

**Solution:**
```bash
sudo chmod 644 /etc/op-connect/token
```
