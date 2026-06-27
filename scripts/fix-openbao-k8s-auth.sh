#!/usr/bin/env bash
# Fix OpenBao Kubernetes auth for k3s-01.
# Refreshes the CA cert and token reviewer JWT so ExternalSecrets can authenticate.
#
# Requires:
#   ROOT_TOKEN env var (from 1Password openbao init recovery material)
#   SSH access to core@10.10.10.50

set -euo pipefail

OPENBAO="http://10.10.10.30:8201"
K3S_HOST="core@10.10.10.50"
K8S_API="https://10.10.10.50:6443"
AUTH_MOUNT="kubernetes-k3s-01"
ROLE="k3s-01-external-secrets"
ES_SA="external-secrets"
ES_NS="external-secrets"

if [[ -z "${ROOT_TOKEN:-}" ]]; then
  echo "ERROR: ROOT_TOKEN is not set. Export it before running:"
  echo "  ROOT_TOKEN=\$(op document get affyyquvnukbgq76zj2s62ndxm --vault Homelab-GitOps | python3 -c \"import json,sys; print(json.load(sys.stdin)['root_token'])\")"
  exit 1
fi

echo "=== Step 1: Fetch k3s-01 CA cert ==="
K8S_CA=$(ssh -o StrictHostKeyChecking=no "$K3S_HOST" \
  'sudo k3s kubectl config view --raw -o jsonpath="{.clusters[0].cluster.certificate-authority-data}"' \
  | base64 -d)
echo "CA subject: $(echo "$K8S_CA" | openssl x509 -noout -subject 2>/dev/null)"

echo ""
echo "=== Step 2: Create 1-year token reviewer JWT ==="
REVIEWER_JWT=$(ssh -o StrictHostKeyChecking=no "$K3S_HOST" \
  "sudo k3s kubectl create token $ES_SA -n $ES_NS \
   --audience=https://kubernetes.default.svc.cluster.local \
   --duration=8760h")
echo "Token obtained (${#REVIEWER_JWT} chars)"

echo ""
echo "=== Step 3: Update OpenBao k8s auth config ==="
PAYLOAD=$(python3 -c "
import json, sys
ca = sys.argv[1]
jwt = sys.argv[2]
print(json.dumps({
    'kubernetes_host': sys.argv[3],
    'kubernetes_ca_cert': ca,
    'token_reviewer_jwt': jwt,
    'disable_iss_validation': True,
    'disable_local_ca_jwt': True,
}))
" "$K8S_CA" "$REVIEWER_JWT" "$K8S_API")

RESULT=$(curl -sf -X POST \
  -H "X-Vault-Token: $ROOT_TOKEN" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD" \
  "$OPENBAO/v1/auth/$AUTH_MOUNT/config" 2>&1) && echo "Config updated (empty = success): $RESULT" \
  || { echo "ERROR updating config: $RESULT"; exit 1; }

echo ""
echo "=== Step 4: Test login ==="
TEST_JWT=$(ssh -o StrictHostKeyChecking=no "$K3S_HOST" \
  "sudo k3s kubectl create token $ES_SA -n $ES_NS \
   --audience=https://kubernetes.default.svc.cluster.local")

LOGIN=$(curl -s -X POST \
  -H "Content-Type: application/json" \
  -d "{\"jwt\":\"$TEST_JWT\",\"role\":\"$ROLE\"}" \
  "$OPENBAO/v1/auth/$AUTH_MOUNT/login")

if echo "$LOGIN" | python3 -c "import json,sys; d=json.load(sys.stdin); assert 'auth' in d and d['auth']" 2>/dev/null; then
  POLICIES=$(echo "$LOGIN" | python3 -c "import json,sys; print(json.load(sys.stdin)['auth']['policies'])")
  echo "LOGIN SUCCESS — policies: $POLICIES"
else
  ERRORS=$(echo "$LOGIN" | python3 -c "import json,sys; print(json.load(sys.stdin).get('errors','unknown'))" 2>/dev/null)
  echo "LOGIN FAILED: $ERRORS"
  exit 1
fi

echo ""
echo "=== Step 5: Force ExternalSecret resync ==="
ssh -o StrictHostKeyChecking=no "$K3S_HOST" \
  "sudo k3s kubectl annotate externalsecret -n democratic-csi \
   democratic-csi-truenas-iscsi-config \
   democratic-csi-truenas-nfs-config \
   force-sync=\"\$(date +%s)\" --overwrite"

echo ""
echo "=== Step 6: Wait 10s and check ExternalSecret status ==="
sleep 10
ssh -o StrictHostKeyChecking=no "$K3S_HOST" \
  "sudo k3s kubectl get externalsecret -n democratic-csi -o wide"
