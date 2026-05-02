#!/bin/bash
set -e

# Function to load env files safely and export variables
load_env() {
    local env_file=$1
    if [ -f "$env_file" ]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            [[ "$line" =~ ^#.*$ ]] && continue
            [[ -z "$line" ]] && continue
            key=$(echo "$line" | cut -d '=' -f 1)
            value=$(echo "$line" | cut -d '=' -f 2- | sed 's/ #.*$//' | sed 's/^"//;s/"$//' | sed "s/^'//;s/'$//")
            export "$key=$value"
        done < "$env_file"
    fi
}

# Function to track execution time
track_time() {
    local start_time=$1
    local end_time=$2
    local task_name=$3
    local duration=$((end_time - start_time))
    echo "Task [$task_name] completed in $((duration / 60))m $((duration % 60))s"
}

# Load Secrets
load_env "config/secrets.env"

# Export standard Ansible VMware vars
export VMWARE_HOST="$VCENTER_SERVER"
export VMWARE_USER="$VCENTER_USERNAME"
export VMWARE_PASSWORD="$VCENTER_PASSWORD"
export VMWARE_VALIDATE_CERTS="no"

COMMAND=$1
PROFILE=${2:-"photon-docker"}
INSTANCE_ID=${3:-"01"}
TARGET_HOST=${4:-"esxi-01.mgmt.plexplease.com"}

case $COMMAND in
    lint)
        START=$(date +%s)
        echo "Starting Configuration Linting for $PROFILE targeting $TARGET_HOST..."
        export RUNTIME_PROFILE="$PROFILE"
        export VCENTER_HOST_OVERRIDE="$TARGET_HOST"
        python3 scripts/lint_config.py
        track_time $START $(date +%s) "Linting"
        ;;

    deploy)
        START=$(date +%s)
        echo "Starting Unified OpenTofu Deployment ($PROFILE)..."
        
        eval $(python3 -c "import yaml, json; c=yaml.safe_load(open('config/profiles/${PROFILE}.yml')); \
            print(f'export TF_VAR_datacenter=\"{c[\"vcenter\"][\"datacenter\"]}\"'); \
            print(f'export TF_VAR_cluster=\"{c[\"vcenter\"][\"cluster\"]}\"'); \
            print(f'export TF_VAR_datastore=\"{c[\"vcenter\"][\"datastore\"]}\"'); \
            print(f'export TF_VAR_network=\"{c[\"vcenter\"][\"network\"]}\"'); \
            print(f'export TF_VAR_vm_cpu=\"{c[\"vm_specs\"][\"cpu\"]}\"'); \
            print(f'export TF_VAR_vm_ram_gb=\"{c[\"vm_specs\"][\"ram_gb\"]}\"'); \
            print(f'export TF_VAR_guest_id=\"{c[\"vm_specs\"][\"guest_id\"]}\"'); \
            print(f'export TF_VAR_disk_size_gb=\"{c[\"vm_specs\"][\"disk_size_gb\"]}\"'); \
            print(f'export TF_VAR_library_name=\"{c[\"content_library\"][\"name\"]}\"'); \
            print(f'export TF_VAR_template_name=\"{c[\"content_library\"][\"template\"]}\"'); \
            print(f'export TF_VAR_mac_address=\"{c[\"deployment\"].get(\"mac_address\", \"\")}\"'); \
            print(f'export VM_PREFIX=\"{c[\"deployment\"][\"vm_name_prefix\"]}\"'); \
            print(f'export VM_INSTANCE=\"{c[\"deployment\"].get(\"vm_instance\", \"01\")}\"'); \
            print(f'export VM_DOMAIN=\"{c[\"deployment\"][\"vm_name_domain\"]}\"');")

        export TF_VAR_vcenter_server="$VCENTER_SERVER"
        export TF_VAR_vcenter_user="$VCENTER_USERNAME"
        export TF_VAR_vcenter_password="$VCENTER_PASSWORD"
        export TF_VAR_host="$TARGET_HOST"

        VM_NAME="${VM_PREFIX}-${INSTANCE_ID}.${VM_DOMAIN}"
        export TF_VAR_vm_name="$VM_NAME"
        
        echo "Targeting VM: $VM_NAME"

        cd tofu
        tofu init
        tofu workspace select "$VM_NAME" 2>/dev/null || tofu workspace new "$VM_NAME"
        tofu apply -auto-approve
        
        VM_IP=$(tofu output -raw vm_ip)
        echo "VM Deployed at $VM_IP"
        
        # Intermediate Test: Connectivity
        python3 ../scripts/test_connectivity.py "$VM_IP"
        
        # Update static inventory for quick configuration if needed
        echo "photon-node ansible_host=$VM_IP ansible_user=$SSH_ADMIN_USERNAME" > ../ansible/inventory.ini
        cd ..
        track_time $START $(date +%s) "Deployment"
        ;;

    config)
        START=$(date +%s)
        echo "Starting Tag-Based Ansible Configuration..."
        cd ansible
        export ANSIBLE_HOST_KEY_CHECKING=False
        ansible-playbook -i inventory/vmware.yml site.yml --extra-vars "ansible_ssh_pass=$SSH_ADMIN_PASSWORD" --ssh-extra-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        cd ..
        track_time $START $(date +%s) "Ansible Configuration"
        ;;

    test)
        START=$(date +%s)
        echo "Starting End-to-End Testing for $PROFILE..."
        # 1. Find IP from inventory/vcenter
        VM_IP=$(python3 -c "import yaml; c=yaml.safe_load(open('ansible/inventory.ini')); print(c.split('ansible_host=')[1].split(' ')[0])")
        
        # 2. Determine which test file to run
        if [[ "$PROFILE" == *"ubuntu"* ]]; then
            TEST_FILE="tests/test_ubuntu.py"
        else
            TEST_FILE="tests/test_photon.py"
        fi
        
        echo "Running pytest against $VM_IP using $TEST_FILE..."
        pytest --hosts="ansible@$VM_IP" --ssh-config="/dev/null" --ssh-extra-args="-o StrictHostKeyChecking=no" --sudo tests/test_common.py "$TEST_FILE"
        track_time $START $(date +%s) "E2E Testing"
        ;;

    all)
        TOTAL_START=$(date +%s)
        $0 lint $PROFILE
        $0 deploy $PROFILE $INSTANCE_ID
        $0 config $PROFILE
        $0 test $PROFILE $INSTANCE_ID
        track_time $TOTAL_START $(date +%s) "TOTAL SYNTHESIS PIPELINE"
        ;;

    *)
        echo "Usage: $0 {lint|deploy|config|all} [profile_name] [instance_id]"
        exit 1
        ;;
esac
