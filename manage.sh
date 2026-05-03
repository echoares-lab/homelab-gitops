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

# Function to validate MAC address
validate_mac() {
    local mac=$1
    if [[ -n "$mac" ]] && ! [[ "$mac" =~ ^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$ ]]; then
        echo "Error: Invalid MAC address format ($mac). Expected xx:xx:xx:xx:xx:xx"
        exit 1
    fi
}

# Load Consolidated Secrets
load_env "config/secrets.env"

# Export standard Ansible VMware vars
export VMWARE_HOST="$VCENTER_SERVER"
export VMWARE_USER="$VCENTER_USERNAME"
export VMWARE_PASSWORD="$VCENTER_PASSWORD"
export VMWARE_VALIDATE_CERTS="no"

# Parse Flags
KEEP=false
ARGS=()
for arg in "$@"; do
    case $arg in
        -k|--keep)
            KEEP=true
            shift
            ;;
        *)
            ARGS+=("$arg")
            ;;
    esac
done

COMMAND=${ARGS[0]}
PROFILE=${ARGS[1]:-"photon-docker"}
INSTANCE_ID=${ARGS[2]:-"01"}
TARGET_HOST=${ARGS[3]:-"esxi-01.mgmt.plexplease.com"}
MAC_OVERRIDE=${ARGS[4]:-""}

validate_mac "$MAC_OVERRIDE"

case $COMMAND in
    build)
        START=$(date +%s)
        echo "Building Golden OVF Template via Packer ($PROFILE)..."
        if [[ "$PROFILE" == *"ubuntu"* ]]; then
            echo "Error: Ubuntu packer build not yet integrated. Use govc capture method."
            exit 1
        else
            PACKER_FILE="packer/photon.pkr.hcl"
        fi
        
        export PKR_VAR_vcenter_server="$VCENTER_SERVER"
        export PKR_VAR_vcenter_username="$VCENTER_USERNAME"
        export PKR_VAR_vcenter_password="$VCENTER_PASSWORD"
        # Map remaining consolidated vars to Packer
        export PKR_VAR_datacenter="$VCENTER_DATACENTER"
        export PKR_VAR_cluster="$VCENTER_CLUSTER"
        export PKR_VAR_datastore="$VCENTER_DATASTORE"
        export PKR_VAR_network="$VCENTER_NETWORK"
        export PKR_VAR_photon_iso_url="$PHOTON_ISO_URL"
        export PKR_VAR_photon_iso_checksum="$PHOTON_ISO_CHECKSUM"
        export PKR_VAR_ssh_username="$SSH_ADMIN_USERNAME"
        export PKR_VAR_ssh_password="$SSH_ADMIN_PASSWORD"
        
        packer init "$PACKER_FILE"
        packer build -var-file="config/secrets.env" "$PACKER_FILE"
        track_time $START $(date +%s) "Packer Build"
        ;;

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
            print(f'export TF_VAR_vm_tags=\"{\",\".join(c[\"deployment\"][\"tags\"])}\"'); \
            print(f'export YAML_MAC=\"{c[\"deployment\"].get(\"mac_address\", \"\")}\"'); \
            print(f'export VM_PREFIX=\"{c[\"deployment\"][\"vm_name_prefix\"]}\"'); \
            print(f'export VM_INSTANCE=\"{c[\"deployment\"].get(\"vm_instance\", \"01\")}\"'); \
            print(f'export VM_DOMAIN=\"{c[\"deployment\"][\"vm_name_domain\"]}\"');")

        export TF_VAR_vcenter_server="$VCENTER_SERVER"
        export TF_VAR_vcenter_user="$VCENTER_USERNAME"
        export TF_VAR_vcenter_password="$VCENTER_PASSWORD"
        export TF_VAR_host="$TARGET_HOST"

        if [[ -n "$MAC_OVERRIDE" ]]; then
            export TF_VAR_mac_address="$MAC_OVERRIDE"
            echo "Using Runtime MAC Address: $MAC_OVERRIDE"
        else
            export TF_VAR_mac_address="$YAML_MAC"
        fi

        VM_NAME="${VM_PREFIX}-${INSTANCE_ID}.${VM_DOMAIN}"
        export TF_VAR_vm_name="$VM_NAME"
        
        echo "Targeting VM: $VM_NAME"

        cd tofu
        tofu init
        tofu workspace select "$VM_NAME" 2>/dev/null || tofu workspace new "$VM_NAME"
        tofu apply -auto-approve
        
        VM_IP=$(tofu output -raw vm_ip)
        echo "VM Deployed at $VM_IP"
        
        python3 ../scripts/test_connectivity.py "$VM_IP"
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
        VM_IP=$(python3 -c "import re; content=open('ansible/inventory.ini').read(); m=re.search(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', content); print(m.group(1)) if m else exit(1)")
        
        echo "Running pytest against $VM_IP using unified test suite..."
        export EXPECTED_MAC="$MAC_OVERRIDE"
        pytest --hosts="ansible@$VM_IP" --ssh-config="/dev/null" --ssh-extra-args="-o StrictHostKeyChecking=no" --sudo tests/test_common.py tests/test_os.py
        track_time $START $(date +%s) "E2E Testing"
        ;;

    destroy)
        if [ "$KEEP" = true ]; then
            echo "Keep flag set. Skipping destruction phase."
            exit 0
        fi
        START=$(date +%s)
        echo "Destroying Deployment ($PROFILE - $INSTANCE_ID)..."
        
        eval $(python3 -c "import yaml, json; c=yaml.safe_load(open('config/profiles/${PROFILE}.yml')); \
            print(f'export TF_VAR_datacenter=\"{c[\"vcenter\"][\"datacenter\"]}\"'); \
            print(f'export TF_VAR_cluster=\"{c[\"vcenter\"][\"cluster\"]}\"'); \
            print(f'export TF_VAR_host=\"{c[\"vcenter\"][\"host\"]}\"'); \
            print(f'export TF_VAR_datastore=\"{c[\"vcenter\"][\"datastore\"]}\"'); \
            print(f'export TF_VAR_network=\"{c[\"vcenter\"][\"network\"]}\"'); \
            print(f'export TF_VAR_vm_cpu=\"{c[\"vm_specs\"][\"cpu\"]}\"'); \
            print(f'export TF_VAR_vm_ram_gb=\"{c[\"vm_specs\"][\"ram_gb\"]}\"'); \
            print(f'export TF_VAR_guest_id=\"{c[\"vm_specs\"][\"guest_id\"]}\"'); \
            print(f'export TF_VAR_disk_size_gb=\"{c[\"vm_specs\"][\"disk_size_gb\"]}\"'); \
            print(f'export TF_VAR_library_name=\"{c[\"content_library\"][\"name\"]}\"'); \
            print(f'export TF_VAR_template_name=\"{c[\"content_library\"][\"template\"]}\"'); \
            print(f'export TF_VAR_vm_tags=\"{\",\".join(c[\"deployment\"][\"tags\"])}\"'); \
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
        
        cd tofu
        tofu workspace select "$VM_NAME" || exit 1
        tofu destroy -auto-approve
        tofu workspace select default
        tofu workspace delete "$VM_NAME"
        cd ..
        track_time $START $(date +%s) "Destruction"
        ;;

    all)
        TOTAL_START=$(date +%s)
        $0 lint $PROFILE $INSTANCE_ID $TARGET_HOST
        $0 deploy $PROFILE $INSTANCE_ID $TARGET_HOST $MAC_OVERRIDE
        $0 config $PROFILE
        $0 test $PROFILE $INSTANCE_ID $TARGET_HOST $MAC_OVERRIDE
        if [ "$KEEP" = false ]; then
            $0 destroy $PROFILE $INSTANCE_ID $TARGET_HOST
        fi
        track_time $TOTAL_START $(date +%s) "TOTAL SYNTHESIS PIPELINE"
        ;;

    *)
        echo "Usage: $0 [-k|--keep] {build|lint|deploy|config|test|destroy|all} [profile_name] [instance_id] [target_host] [mac_address]"
        echo "Options:"
        echo "  -k, --keep    Skip the destruction phase at the end of 'all' or explicit 'destroy'."
        exit 1
        ;;
esac
