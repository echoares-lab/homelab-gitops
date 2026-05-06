#!/bin/bash
set -e

# ==========================================================
# 1. HELPER FUNCTIONS
# ==========================================================

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

# Function to show comprehensive help
show_help() {
    echo "Unified HomeLab GitOps Orchestrator"
    echo "Usage: $0 [flags] {command} [profile] [id] [overrides]"
    echo ""
    echo "Core Commands:"
    echo "  build       Build a Golden OVF template via Packer (Photon only currently)"
    echo "  lint        Validate YAML profile and vCenter infrastructure objects"
    echo "  deploy      Provision virtual hardware via OpenTofu (Isolated Workspaces)"
    echo "  config      Apply post-deployment configuration via Ansible"
    echo "  test        Run Pytest-Testinfra OS and service validation"
    echo "  destroy     Remove VM and its isolated Tofu workspace"
    echo "  all         Full pipeline: Lint -> Deploy -> Config -> Test -> Destroy (unless -k)"
    echo ""
    echo "Options & Flags:"
    echo "  -h, --help           Show this help menu"
    echo "  -k, --keep           Skip 'destroy' phase at end of 'all' or explicit 'destroy'"
    echo "  --limit <type>       Ansible filter: 'profile' (e.g. tag_ubuntu), 'instance' (FQDN), or 'none' (default)"
    echo ""
    echo "Runtime Overrides:"
    echo "  --host <name>        Override target ESXi host"
    echo "  --mac <addr>         Override network MAC address"
    echo "  --ip <addr>          Set static IPv4 (Enables Guest Customization)"
    echo "  --hostname <name>    Override VM hostname"
    echo "  --gateway <addr>     Set IPv4 gateway (Required for --ip)"
    echo "  --dns <addr>         Set DNS server (Default: 8.8.8.8)"
    echo ""
    echo "Examples:"
    echo "  1. Full Synthesis (DHCP):"
    echo "     $0 all ubuntu-base 01"
    echo ""
    echo "  2. Static IP Deployment with Instance Limit:"
    echo "     $0 deploy photon-docker 02 --ip 10.10.10.50 --gateway 10.10.10.1 --limit instance"
    echo ""
    echo "  3. Interactive Mode (Builder):"
    echo "     $0"
    exit 0
}

# Function for Interactive Mode
interactive_mode() {
    echo "--- HomeLab GitOps Command Builder ---"
    
    # 1. Pick Command
    PS3="Select Command: "
    options=("build" "lint" "deploy" "config" "test" "destroy" "all" "Quit")
    select opt in "${options[@]}"; do
        case $opt in
            "Quit") exit 0 ;;
            *) I_COMMAND=$opt; break ;;
        esac
    done

    # 2. Pick Profile
    echo ""
    echo "Available Profiles:"
    profiles=($(ls config/profiles/*.yml | xargs -n 1 basename | sed 's/\.yml//'))
    PS3="Select Profile: "
    select prof in "${profiles[@]}"; do
        if [[ -n "$prof" ]]; then I_PROFILE=$prof; break; fi
    done

    # 3. Instance ID
    echo ""
    read -p "Instance ID [01]: " I_ID
    I_ID=${I_ID:-"01"}

    # 4. Optional Overrides
    I_FLAGS=""
    echo ""
    read -p "Override Host? (Leave empty for default): " I_HOST
    [[ -n "$I_HOST" ]] && I_FLAGS+=" --host $I_HOST"

    read -p "Set Static IP? (e.g. 10.10.10.50, empty for DHCP): " I_IP
    if [[ -n "$I_IP" ]]; then
        I_FLAGS+=" --ip $I_IP"
        read -p "  Gateway [10.10.10.1]: " I_GW
        I_FLAGS+=" --gateway ${I_GW:-"10.10.10.1"}"
    fi

    read -p "Custom MAC? (xx:xx...): " I_MAC
    if [[ -n "$I_MAC" ]]; then
        validate_mac "$I_MAC"
        I_FLAGS+=" --mac $I_MAC"
    fi

    read -p "Limit Ansible to this instance? (y/N): " I_LIM
    [[ "$I_LIM" =~ ^[Yy]$ ]] && I_FLAGS+=" --limit instance"

    echo ""
    FULL_CMD="./manage.sh $I_COMMAND $I_PROFILE $I_ID $I_FLAGS"
    echo "Constructed Command: $FULL_CMD"
    echo "---------------------------------------"
    
    # Execute
    $FULL_CMD
    echo ""
    echo "Execution Summary: $FULL_CMD"
    exit 0
}

# ==========================================================
# 2. INITIALIZATION & PARSING
# ==========================================================

# Enter interactive mode if no arguments
if [[ "$#" -eq 0 ]]; then
    interactive_mode
fi

# Load Consolidated Secrets
load_env "config/secrets.env"

# Defaults
KEEP=false
PROFILE=""
INSTANCE_ID=""
TARGET_HOST="esxi-01.mgmt.plexplease.com"
MAC_OVERRIDE=""
IP_OVERRIDE=""
HOSTNAME_OVERRIDE=""
NETMASK="24"
GATEWAY=""
DNS="8.8.8.8"
LIMIT="none"
COMMAND=""

# Parse flags and positional arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -h|--help) show_help ;;
        -k|--keep) KEEP=true ;;
        --ip) IP_OVERRIDE="$2"; shift ;;
        --hostname) HOSTNAME_OVERRIDE="$2"; shift ;;
        --mac) MAC_OVERRIDE="$2"; shift ;;
        --host) TARGET_HOST="$2"; shift ;;
        --netmask) NETMASK="$2"; shift ;;
        --gateway) GATEWAY="$2"; shift ;;
        --dns) DNS="$2"; shift ;;
        --limit) LIMIT="$2"; shift ;;
        -*) echo "Unknown flag: $1"; exit 1 ;;
        *)
            if [[ -z "$COMMAND" ]]; then
                COMMAND="$1"
            elif [[ -z "$PROFILE" ]]; then
                PROFILE="$1"
            elif [[ -z "$INSTANCE_ID" ]]; then
                INSTANCE_ID="$1"
            else
                echo "Unknown argument: $1"
                exit 1
            fi
            ;;
    esac
    shift
done

# Validate positional arguments
if [[ -z "$COMMAND" ]]; then show_help; fi

# Set defaults for profile/id
if [[ "$COMMAND" != "build" && "$COMMAND" != "config" ]]; then
    PROFILE=${PROFILE:-"photon-docker"}
    INSTANCE_ID=${INSTANCE_ID:-"01"}
fi

validate_mac "$MAC_OVERRIDE"

# Load profile data for Name construction
if [[ -f "config/profiles/${PROFILE}.yml" ]]; then
    eval $(python3 -c "import yaml; c=yaml.safe_load(open('config/profiles/${PROFILE}.yml')); \
        print(f'VM_PREFIX=\"{c[\"deployment\"][\"vm_name_prefix\"]}\"'); \
        print(f'VM_DOMAIN=\"{c[\"deployment\"][\"vm_name_domain\"]}\"');")
    
    if [[ -n "$HOSTNAME_OVERRIDE" ]]; then
        VM_NAME="${HOSTNAME_OVERRIDE}.${VM_DOMAIN}"
    else
        VM_NAME="${VM_PREFIX}-${INSTANCE_ID}.${VM_DOMAIN}"
    fi
fi

# ==========================================================
# 3. COMMAND EXECUTION
# ==========================================================

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
            print(f'export YAML_MAC=\"{c[\"deployment\"].get(\"mac_address\", \"\")}\"');")

        export TF_VAR_vcenter_server="$VCENTER_SERVER"
        export TF_VAR_vcenter_user="$VCENTER_USERNAME"
        export TF_VAR_vcenter_password="$VCENTER_PASSWORD"
        export TF_VAR_host="$TARGET_HOST"
        export TF_VAR_vm_name="$VM_NAME"

        # Overrides
        [[ -n "$MAC_OVERRIDE" ]] && export TF_VAR_mac_address="$MAC_OVERRIDE" || export TF_VAR_mac_address="$YAML_MAC"
        export TF_VAR_ipv4_address="$IP_OVERRIDE"
        export TF_VAR_ipv4_netmask="$NETMASK"
        export TF_VAR_ipv4_gateway="$GATEWAY"
        export TF_VAR_dns_servers="[\"$DNS\"]"

        echo "Targeting VM: $VM_NAME"
        [[ -n "$IP_OVERRIDE" ]] && echo "Static IP: $IP_OVERRIDE"

        cd tofu
        tofu init
        tofu workspace select "$VM_NAME" 2>/dev/null || tofu workspace new "$VM_NAME"
        tofu apply -auto-approve
        
        VM_IP=$(tofu output -raw vm_ip)
        echo "VM Deployed at $VM_IP"
        
        python3 ../scripts/test_connectivity.py "$VM_IP"
        # Update static inventory for quick access
        echo "node ansible_host=$VM_IP ansible_user=$SSH_ADMIN_USERNAME" > ../ansible/inventory.ini
        cd ..
        track_time $START $(date +%s) "Deployment"
        ;;

    config)
        START=$(date +%s)
        echo "Starting Tag-Based Ansible Configuration..."
        
        # Determine Limit
        LIMIT_ARG=""
        if [[ "$LIMIT" == "profile" ]]; then
            LIMIT_ARG="-l tag_$PROFILE"
        elif [[ "$LIMIT" == "instance" ]]; then
            LIMIT_ARG="-l $VM_NAME"
        fi
        
        echo "Filter: ${LIMIT_ARG:-"None"}"
        
        cd ansible
        export ANSIBLE_HOST_KEY_CHECKING=False
        ansible-playbook -i inventory/vmware_vms.yml site.yml $LIMIT_ARG \
            --private-key "$SSH_PRIVATE_KEY_PATH" \
            --extra-vars "ansible_ssh_pass=$SSH_ADMIN_PASSWORD" \
            --ssh-extra-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        cd ..
        track_time $START $(date +%s) "Ansible Configuration"
        ;;

    test)
        START=$(date +%s)
        echo "Starting End-to-End Testing for $PROFILE..."
        VM_IP=$(python3 -c "import re; content=open('ansible/inventory.ini').read(); m=re.search(r'([0-9]+\.[0-9]+\.[0-9]+\.[0-9]+)', content); print(m.group(1)) if m else exit(1)")
        
        echo "Running pytest against $VM_IP using unified test suite..."
        export EXPECTED_MAC="$MAC_OVERRIDE"
        pytest --hosts="ansible@$VM_IP" --ssh-config="/dev/null" --ssh-extra-args="-o StrictHostKeyChecking=no -o IdentityFile=$SSH_PRIVATE_KEY_PATH" --sudo tests/test_common.py tests/test_os.py
        track_time $START $(date +%s) "E2E Testing"
        ;;

    destroy)
        if [ "$KEEP" = true ]; then
            echo "Keep flag set. Skipping destruction phase."
            exit 0
        fi
        START=$(date +%s)
        echo "Destroying Workspace: $VM_NAME"
        cd tofu
        tofu workspace select "$VM_NAME" || exit 1
        tofu destroy -auto-approve \
            -var="vcenter_server=$VCENTER_SERVER" \
            -var="vcenter_user=$VCENTER_USERNAME" \
            -var="vcenter_password=$VCENTER_PASSWORD" \
            -var="datacenter=x" -var="cluster=x" -var="host=x" -var="datastore=x" -var="network=x" \
            -var="vm_name=$VM_NAME" -var="vm_cpu=1" -var="vm_ram_gb=1" \
            -var="guest_id=x" -var="library_name=x" -var="template_name=x" -var="vm_tags=x"
        tofu workspace select default
        tofu workspace delete "$VM_NAME"
        cd ..
        track_time $START $(date +%s) "Destruction"
        ;;

    all)
        TOTAL_START=$(date +%s)
        $0 lint $PROFILE $INSTANCE_ID --host "$TARGET_HOST"
        $0 deploy $PROFILE $INSTANCE_ID --host "$TARGET_HOST" --mac "$MAC_OVERRIDE" --ip "$IP_OVERRIDE" --hostname "$HOSTNAME_OVERRIDE" --netmask "$NETMASK" --gateway "$GATEWAY" --dns "$DNS"
        $0 config $PROFILE --limit "$LIMIT"
        $0 test $PROFILE $INSTANCE_ID --mac "$MAC_OVERRIDE"
        if [ "$KEEP" = false ]; then
            $0 destroy $PROFILE $INSTANCE_ID --hostname "$HOSTNAME_OVERRIDE"
        fi
        track_time $TOTAL_START $(date +%s) "TOTAL SYNTHESIS PIPELINE"
        ;;

    *)
        show_help
        ;;
esac
