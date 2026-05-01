#!/bin/bash
set -e

# --- Configuration ---
# Using Ubuntu 26.04 (Resolute) Cloud Image
CLOUD_IMG_URL="https://cloud-images.ubuntu.com/releases/26.04/release/ubuntu-26.04-server-cloudimg-amd64.img"
CLOUD_IMG_FILE="ubuntu-26.04-cloudimg.img"
DISK_IMAGE="ubuntu-26.04.qcow2"
CIDATA_ISO="cidata.iso"

# Load vCenter config from environment or defaults
[ -f ../config/defaults.env ] && source ../config/defaults.env
[ -f ../config/inputs.env ] && source ../config/inputs.env

# --- Tool Check ---
# Local govc check/download
if ! command -v govc &> /dev/null && [ ! -f "./govc" ]; then
    echo "govc not found, downloading locally..."
    curl -L https://github.com/vmware/govmomi/releases/latest/download/govc_Linux_x86_64.tar.gz | tar -xvzf - govc
fi
GOVC_BIN=$(command -v govc || echo "./govc")

MISSING_TOOLS=()
for tool in genisoimage qemu-img curl tar sha256sum; do
    if ! command -v $tool &> /dev/null; then
        MISSING_TOOLS+=("$tool")
    fi
done

if [ ${#MISSING_TOOLS[@]} -ne 0 ]; then
    echo "Error: The following tools are missing: ${MISSING_TOOLS[*]}"
    exit 1
fi

# --- Image Download ---
if [ ! -f "$CLOUD_IMG_FILE" ]; then
    echo "Downloading Ubuntu 26.04 Cloud Image..."
    curl -L -o "$CLOUD_IMG_FILE" "$CLOUD_IMG_URL"
fi

# --- Prepare Disk ---
echo "Creating working copy of the image..."
cp "$CLOUD_IMG_FILE" "$DISK_IMAGE"

echo "Resizing image to 20G..."
qemu-img resize "$DISK_IMAGE" 20G

# --- Create CIDATA ---
echo "Generating CIDATA ISO for cloud-init..."
# This will be used by the VM on its first boot after deployment
genisoimage -output "$CIDATA_ISO" -volid cidata -joliet -rock user-data meta-data

# --- Versioning and Metadata ---
CL_NAME=${CONTENT_LIBRARY_NAME:-"Templates"}
BASE_ITEM_NAME=${CONTENT_LIBRARY_ITEM_NAME:-"ubuntu-26.04"}
ITEM_NAME="$BASE_ITEM_NAME"
VERSION_STRING="1.0.0"

if [ -n "$VCENTER_SERVER" ]; then
    export GOVC_URL="$VCENTER_SERVER"
    export GOVC_USERNAME="$VCENTER_USERNAME"
    export GOVC_PASSWORD="$VCENTER_PASSWORD"
    export GOVC_INSECURE=true

    echo "Checking for existing item: $CL_NAME/$ITEM_NAME"
    VERSION=1
    while "$GOVC_BIN" library.ls "$CL_NAME/" | grep -Fqx "/${CL_NAME}/${ITEM_NAME}"; do
        ITEM_NAME="${BASE_ITEM_NAME}-v${VERSION}"
        VERSION_STRING="1.0.${VERSION}"
        echo "Item already exists. Trying versioned name: $ITEM_NAME"
        VERSION=$((VERSION + 1))
    done
fi

DISK_VMDK="${ITEM_NAME}.vmdk"
OVF_FILE="${ITEM_NAME}.ovf"
MF_FILE="${ITEM_NAME}.mf"
OVA_FILE="${ITEM_NAME}.ova"

# --- Convert Disk ---
echo "Converting disk to VMDK ($DISK_VMDK)..."
qemu-img convert -f qcow2 -O vmdk -o subformat=streamOptimized "$DISK_IMAGE" "$DISK_VMDK"

# --- Package OVA ---
echo "Creating OVF descriptor ($OVF_FILE) with metadata..."
DISK_SIZE_BYTES=$(stat -c%s "$DISK_VMDK")
ITEM_DESC=${CONTENT_LIBRARY_DESCRIPTION:-"Ubuntu 26.04 LTS minimal golden image"}

sed -e "s/SIZE_PLACEHOLDER/$DISK_SIZE_BYTES/" \
    -e "s/DESCRIPTION_PLACEHOLDER/$ITEM_DESC/" \
    -e "s/VERSION_PLACEHOLDER/$VERSION_STRING/" \
    -e "s/ubuntu-26.04/$ITEM_NAME/g" \
    template.ovf > "$OVF_FILE"

echo "Generating Manifest ($MF_FILE)..."
sha256sum "$OVF_FILE" "$DISK_VMDK" | awk '{print "SHA256(" $2 ")=" $1}' > "$MF_FILE"

echo "Packaging OVA ($OVA_FILE)..."
tar -cf "$OVA_FILE" "$OVF_FILE" "$MF_FILE" "$DISK_VMDK"

# --- Upload to Content Library ---
if [ -n "$VCENTER_SERVER" ]; then
    echo "Importing $OVA_FILE to library $CL_NAME as $ITEM_NAME..."
    "$GOVC_BIN" library.import -n "$ITEM_NAME" "$CL_NAME" "$OVA_FILE"
    echo "Updating item metadata..."
    "$GOVC_BIN" library.update -d "$ITEM_DESC" "$CL_NAME/$ITEM_NAME"
else
    echo "VCENTER_SERVER not set, skipping upload."
    echo "OVA available at $OVA_FILE"
fi

echo "Build complete!"
