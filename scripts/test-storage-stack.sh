#!/usr/bin/env bash
# End-to-end test of the storage stack on k3s-01.
# Tests: ArgoCD sync → ClusterSecretStore → ExternalSecrets → StorageClasses → PVC provisioning
set -euo pipefail

K3S="ssh -o StrictHostKeyChecking=no core@10.10.10.50 sudo k3s kubectl"
PASS=0; FAIL=0; true

check() {
  local label="$1"; local cmd="$2"; local expect="$3"
  local result
  result=$(eval "$cmd" 2>&1) || true
  if echo "$result" | grep -q "$expect"; then
    echo "  PASS  $label"
    PASS=$((PASS+1))
  else
    echo "  FAIL  $label"
    echo "        expected: $expect"
    echo "        got:      $result"
    FAIL=$((FAIL+1))
  fi
}

echo "=== 1. ArgoCD sync status ==="
$K3S get application -n argocd -o wide 2>/dev/null | head -20 || \
  $K3S get application.argoproj.io -n argocd 2>/dev/null | head -20

echo ""
echo "=== 2. ClusterSecretStore ==="
$K3S get clustersecretstore openbao -o jsonpath='{.status.conditions[0]}' | python3 -m json.tool
check "ClusterSecretStore ready" \
  "$K3S get clustersecretstore openbao -o jsonpath='{.status.conditions[0].reason}'" \
  "Valid"

echo ""
echo "=== 3. ExternalSecrets ==="
$K3S get externalsecret -A -o wide
check "iscsi secret synced" \
  "$K3S get externalsecret -n democratic-csi democratic-csi-truenas-iscsi-config -o jsonpath='{.status.conditions[0].reason}'" \
  "SecretSynced"
check "nfs secret synced" \
  "$K3S get externalsecret -n democratic-csi democratic-csi-truenas-nfs-config -o jsonpath='{.status.conditions[0].reason}'" \
  "SecretSynced"

echo ""
echo "=== 4. democratic-csi driver pods ==="
$K3S get pods -n democratic-csi -o wide

echo ""
echo "=== 5. StorageClasses ==="
$K3S get storageclass

echo ""
echo "=== 6. PVC smoke tests ==="

# Fast tier (local ZFS)
$K3S apply -f - <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: smoke-fast
  namespace: default
spec:
  storageClassName: storage-fast
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
YAML

# Standard tier (iSCSI) - only if iscsi secret exists
if $K3S get secret -n democratic-csi democratic-csi-truenas-iscsi-config &>/dev/null; then
  $K3S apply -f - <<'YAML'
apiVersion: v1
kind: PersistentVolumeClaim
metadata:
  name: smoke-standard
  namespace: default
spec:
  storageClassName: storage-standard
  accessModes: [ReadWriteOnce]
  resources:
    requests:
      storage: 1Gi
YAML
fi

echo "  Waiting 20s for PVCs to bind..."
sleep 20

$K3S get pvc -n default smoke-fast smoke-standard 2>/dev/null || \
  $K3S get pvc -n default smoke-fast 2>/dev/null

check "smoke-fast PVC bound" \
  "$K3S get pvc -n default smoke-fast -o jsonpath='{.status.phase}'" \
  "Bound"

# Check standard only if it was created
if $K3S get pvc -n default smoke-standard &>/dev/null 2>&1; then
  check "smoke-standard PVC bound" \
    "$K3S get pvc -n default smoke-standard -o jsonpath='{.status.phase}'" \
    "Bound"
fi

echo ""
echo "=== 7. Cleanup ==="
$K3S delete pvc -n default smoke-fast smoke-standard 2>/dev/null || \
  $K3S delete pvc -n default smoke-fast 2>/dev/null || true

echo ""
echo "================================"
echo "  Results: $PASS passed, $FAIL failed"
echo "================================"
[[ $FAIL -eq 0 ]]
