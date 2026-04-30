#!/bin/bash
# Wrapper to run Packer with env vars loaded

# Load defaults then inputs
if [ -f "config/defaults.env" ]; then
    export $(grep -v '^#' config/defaults.env | xargs)
fi

if [ -f "config/inputs.env" ]; then
    export $(grep -v '^#' config/inputs.env | xargs)
else
    echo "Warning: config/inputs.env not found. Using defaults only."
fi

cd packer
packer init .
packer build ubuntu-server.pkr.hcl
