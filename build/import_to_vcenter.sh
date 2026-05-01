#!/bin/bash
set -e
[ -f ../config/defaults.env ] && source ../config/defaults.env
[ -f ../config/inputs.env ] && source ../config/inputs.env

GOVC_BIN=$(command -v govc || echo "./govc")
OVA_FILE="ubuntu-26.04.ova"

if [ -n "$VCENTER_SERVER" ]; then
    export GOVC_URL="$VCENTER_SERVER"
    export GOVC_USERNAME="$VCENTER_USERNAME"
    export GOVC_PASSWORD="$VCENTER_PASSWORD"
    export GOVC_INSECURE=true

    CL_NAME=${CONTENT_LIBRARY_NAME:-"Templates"}
    ITEM_NAME=${CONTENT_LIBRARY_ITEM_NAME:-"ubuntu-26.04"}
    
    ITEM_PATH="$CL_NAME/$ITEM_NAME"
    
    echo "Checking for existing item: $ITEM_PATH"
    # Check if item exists
    if "$GOVC_BIN" library.ls "$ITEM_PATH" &>/dev/null; then
        echo "Deleting existing library item $ITEM_NAME..."
        "$GOVC_BIN" library.rm "$ITEM_PATH"
    fi

    echo "Importing $OVA_FILE to library $CL_NAME..."
    "$GOVC_BIN" library.import "$CL_NAME" "$OVA_FILE"
else
    echo "VCENTER_SERVER not set, skipping upload."
fi
