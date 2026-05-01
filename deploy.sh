#!/bin/bash
# Wrapper to run Ansible deployment with env vars loaded

DEPLOY_START_TIME=$(date +%s)

# Function to load env files safely
load_env() {
    local env_file=$1
    if [ -f "$env_file" ]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ "$line" =~ ^#.*$ ]] && continue
            [[ -z "$line" ]] && continue
            
            # Extract key and value
            key=$(echo "$line" | cut -d '=' -f 1)
            value=$(echo "$line" | cut -d '=' -f 2- | sed 's/^"//;s/"$//') # Remove quotes
            
            export "$key=$value"
        done < "$env_file"
    fi
}

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -n|--name) RUNTIME_VM_NAME="$2"; shift ;;
        -k|--keep) KEEP_ARTIFACT=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

load_env "config/defaults.env"
if [ -f "config/inputs.env" ]; then
    load_env "config/inputs.env"
else
    echo "Warning: config/inputs.env not found. Using defaults only."
fi

# Determine folder: use test folder if not prod naming
if [[ "$RUNTIME_VM_NAME" == *"-prod-"* ]]; then
    export RUNTIME_DEPLOY_FOLDER="$VCENTER_DEPLOY_PROD_FOLDER"
else
    export RUNTIME_DEPLOY_FOLDER="$VCENTER_DEPLOY_TEST_FOLDER"
fi

# Export runtime variables
if [ -n "$RUNTIME_VM_NAME" ]; then
    export RUNTIME_VM_NAME
fi

# Run Ansible to deploy the VM
ansible-playbook ansible/deploy.yml

# Read the IP from the temporary file
DEPLOY_VM_IP=""
if [ -f "/tmp/last_vm_ip" ]; then
    DEPLOY_VM_IP=$(cat /tmp/last_vm_ip)
    rm /tmp/last_vm_ip
fi

if [ -z "$DEPLOY_VM_IP" ]; then
    echo "Error: Could not determine VM IP address. Deployment aborted."
    exit 1
fi

TARGET_HOST="$DEPLOY_VM_IP"

echo "Waiting for SSH on $TARGET_HOST..."
until nc -zvw1 "$TARGET_HOST" 22; do
    echo "Still waiting for SSH on $TARGET_HOST..."
    sleep 5
done
echo "SSH is up on $TARGET_HOST!"

echo "Creating inventory for $NODE_HOSTNAME"
echo "$NODE_HOSTNAME ansible_host=$DEPLOY_VM_IP ansible_user=$SSH_ADMIN_USERNAME" > ansible/inventory.ini
# Run the configuration roles with host key checking disabled
export ANSIBLE_HOST_KEY_CHECKING=False
ansible-playbook -i ansible/inventory.ini ansible/configure.yml \
    --extra-vars "ansible_ssh_pass=$PACKER_SSH_PASSWORD" \
    --ssh-extra-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'

# End timing
DEPLOY_END_TIME=$(date +%s)
DEPLOY_DURATION=$((DEPLOY_END_TIME - DEPLOY_START_TIME))
echo "Deployment completed in $((DEPLOY_DURATION / 60))m $((DEPLOY_DURATION % 60))s"
