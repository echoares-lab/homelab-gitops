#!/bin/bash
# Export ubuntu-24.04-golden-build template to GOLDEN content library
# Usage: export-to-golden.sh <vcenter-server> <username> <password>

set -e

VCENTER_SERVER="${1:-10.10.10.9}"
VCENTER_USERNAME="${2:-administrator@vsphere.local}"
VCENTER_PASSWORD="${3:-Singer4life!@}"

TEMPLATE_NAME="ubuntu-24.04-golden-build"
LIBRARY_NAME="GOLDEN"
ITEM_NAME="ubuntu-24.04-lts-golden"

echo "[*] Configuring govc environment..."
export GOVC_URL="${VCENTER_USERNAME}:${VCENTER_PASSWORD}@${VCENTER_SERVER}"
export GOVC_INSECURE=1

echo "[*] Verifying template exists: $TEMPLATE_NAME"
if ! govc vm.info "/HOMELAB/vm/$TEMPLATE_NAME" &>/dev/null; then
  echo "❌ Template not found: /HOMELAB/vm/$TEMPLATE_NAME"
  exit 1
fi
echo "✅ Template found"

echo "[*] Getting library ID for $LIBRARY_NAME..."
LIBRARY_ID=$(govc library.ls -json | jq -r ".[] | select(.name==\"$LIBRARY_NAME\") | .id" 2>/dev/null || echo "")

if [ -z "$LIBRARY_ID" ]; then
  echo "❌ Library not found: $LIBRARY_NAME"
  exit 1
fi
echo "✅ Library found (ID: $LIBRARY_ID)"

echo "[*] Exporting template to content library..."
python3 << PYEOF
import json
import subprocess
import time

def run_cmd(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"Error: {result.stderr}")
        raise Exception(f"Command failed: {cmd}")
    return result.stdout.strip()

# Get the template VM info
try:
    vm_info_json = run_cmd('govc vm.info -json "/HOMELAB/vm/$TEMPLATE_NAME"')
    vm_info = json.loads(vm_info_json)
    vm_uuid = vm_info['VMs'][0]['Config']['Uuid']
    print(f"✅ Template UUID: {vm_uuid}")
except Exception as e:
    print(f"❌ Failed to get template info: {e}")
    exit(1)

# Check if item already exists
try:
    items_json = run_cmd('govc library.item.ls -json "$LIBRARY_ID"')
    items = json.loads(items_json)
    for item in items:
        if item.get('name') == '$ITEM_NAME':
            print(f"⚠️  Item already exists: $ITEM_NAME (ID: {item['id']})")
            print("Skipping export. Item exists in library.")
            exit(0)
except Exception as e:
    print(f"Note: Could not check existing items: {e}")

# Export the template using govc export
print("[*] Exporting VM as OVF...")
export_cmd = 'govc export.ovf -vm "/HOMELAB/vm/$TEMPLATE_NAME" "/tmp/$ITEM_NAME"'
run_cmd(export_cmd)

# Import OVF to library
print("[*] Importing OVF to content library...")
import_cmd = f'govc library.import "$LIBRARY_ID" "/tmp/$ITEM_NAME/$TEMPLATE_NAME.ovf"'
result = subprocess.run(import_cmd, shell=True, capture_output=True, text=True)

if result.returncode == 0:
    print(f"✅ Successfully exported template to GOLDEN library as {$ITEM_NAME}")
else:
    print(f"Note: Import status - {result.stdout}")
    if "exists" in result.stderr.lower() or "already" in result.stderr.lower():
        print("ℹ️  Item may already exist in library")
    else:
        print(f"Warning: {result.stderr}")

PYEOF

echo "✅ Export process completed"
