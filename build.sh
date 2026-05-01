#!/bin/bash
set -e

# Wrapper to run the new QEMU-based build pipeline

# Load configurations
if [ -f "config/defaults.env" ]; then
    source config/defaults.env
fi

if [ -f "config/inputs.env" ]; then
    source config/inputs.env
else
    echo "Warning: config/inputs.env not found. Using defaults only."
fi

echo "----------------------------------------------------------"
echo " Starting QEMU Build & vCenter Content Library Upload "
echo "----------------------------------------------------------"

BUILD_START_TIME=$(date +%s)

# Execute the build orchestration script
cd build
./build_ovf.sh

BUILD_END_TIME=$(date +%s)
BUILD_DURATION=$((BUILD_END_TIME - BUILD_START_TIME))

echo "----------------------------------------------------------"
echo " Build completed in $((BUILD_DURATION / 60))m $((BUILD_DURATION % 60))s"
echo "----------------------------------------------------------"
