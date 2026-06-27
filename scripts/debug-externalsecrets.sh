#!/usr/bin/env bash
# Diagnose ExternalSecret sync failures after OpenBao auth is fixed.
set -euo pipefail

K3S="ssh -o StrictHostKeyChecking=no core@10.10.10.50 sudo k3s kubectl"

echo "=== ClusterSecretStore status ==="
$K3S get clustersecretstore openbao -o jsonpath='{.status}' | python3 -m json.tool

echo ""
echo "=== ExternalSecret: iscsi (events + status) ==="
$K3S describe externalsecret -n democratic-csi democratic-csi-truenas-iscsi-config | grep -A 30 "Status\|Events"

echo ""
echo "=== ExternalSecret: nfs (events + status) ==="
$K3S describe externalsecret -n democratic-csi democratic-csi-truenas-nfs-config | grep -A 30 "Status\|Events"

echo ""
echo "=== OpenBao KV paths (check they exist) ==="
echo "  Checking with root token from env..."
curl -sf -H "X-Vault-Token: $ROOT_TOKEN" \
  "http://10.10.10.30:8201/v1/secret/metadata/k3s-01?list=true" \
  | python3 -m json.tool 2>/dev/null || echo "  Path secret/k3s-01 not found or error"

echo ""
echo "=== ExternalSecrets operator logs (last 30 lines) ==="
$K3S logs -n external-secrets deploy/external-secrets --tail=30 2>/dev/null || \
  $K3S logs -n external-secrets -l app.kubernetes.io/name=external-secrets --tail=30
