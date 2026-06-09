# Secrets Management Runbook

Operational procedures for managing 1Password Connect and secrets.

## Health Checks

### Daily

```bash
# Check Connect server is responding
curl https://{connect-hostname}:8200/health | jq .

# Check token file exists and has correct permissions
ls -la /etc/op-connect/token
# Expected: -rw-r--r-- 1 root root

# Check logs
tail -20 /var/log/op-connect/access.log | jq .
```

### Weekly

```bash
# Review access logs for anomalies
grep "denied\|error" /var/log/op-connect/access.log

# Verify all vaults are accessible
export OP_CONNECT_TOKEN=$(cat /etc/op-connect/token)
op run --server https://{connect-hostname}:8200 -- op vault list
```

## Rotating Connect Token

When: Token compromised, team member leaves, annual rotation

Steps:
1. **Generate new token in 1Password**
   - Go to Settings → Developer → API Tokens
   - Create new token for "1Password Connect"
   - Copy to clipboard

2. **Update token file**
   ```bash
   sudo cp /etc/op-connect/token /etc/op-connect/token.old
   echo "ops_NEW_TOKEN" | sudo tee /etc/op-connect/token > /dev/null
   sudo chmod 644 /etc/op-connect/token
   ```

3. **Restart Connect**
   ```bash
   docker -H {docker-host} restart op-connect-api op-connect-sync
   ```

4. **Verify new token works**
   ```bash
   export OP_CONNECT_TOKEN=$(cat /etc/op-connect/token)
   curl -s -H "Authorization: Bearer ${OP_CONNECT_TOKEN}" \
     https://{connect-hostname}:8200/health
   # Expected: 200 OK
   ```

5. **Revoke old token**
   - Go to 1Password Settings → Developer → API Tokens
   - Delete old token

6. **Document rotation**
   ```bash
   echo "$(date): Token rotated (rotation reason)" >> /var/log/op-connect/rotations.log
   ```

## Adding New Secret

1. Go to 1Password vault (e.g., `op://homelab-gitops/`)
2. Navigate to appropriate folder (dev/, prod/, or ci/)
3. Click "+" to add new item
4. Fill in fields:
   - Name: Environment variable name (e.g., `NEW_API_KEY`)
   - Value: Actual secret
5. Save

## Emergency: Lost/Compromised Token

If /etc/op-connect/token is lost or compromised:

1. Generate new token in 1Password (as described in "Rotating Connect Token")
2. Update /etc/op-connect/token with new value
3. Restart Connect and verify
4. Invalidate compromised token in 1Password immediately

## Audit Logging

Access logs are stored at: `/var/log/op-connect/access.log`

Example log entry:
```json
{
  "timestamp": "2026-06-08T14:32:15Z",
  "role": "ci",
  "vault": "homelab-gitops",
  "item": "prod/VCENTER_PASSWORD",
  "action": "read",
  "status": "authorized"
}
```

Monthly review process:
1. Export logs to CSV for analysis
2. Check for denied access attempts
3. Verify all prod/ci access is expected
4. Flag any anomalies
