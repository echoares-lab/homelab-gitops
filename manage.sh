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

# Pre-flight check for secrets
check_secrets() {
    if [ ! -f "config/secrets.env" ]; then
        echo "Error: 'config/secrets.env' not found."
        echo "Hint: Copy 'config/secrets.env.example' to 'config/secrets.env' and fill in your credentials."
        exit 1
    fi
    # Check for redacted values
    if grep -q "REDACTED" "config/secrets.env"; then
        echo "Error: 'config/secrets.env' contains REDACTED values."
        echo "Hint: Open the file and replace REDACTED placeholders with real vCenter/SSH credentials."
        exit 1
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
        echo "Error: Invalid MAC address format ($mac)."
        echo "Hint: MAC must be in the format xx:xx:xx:xx:xx:xx"
        exit 1
    fi
}

# Function for Identifying VM Workspace for Destruction
identify_vm() {
    local target=$1
    
    # 1. Check for exact workspace match
    cd tofu > /dev/null
    local ws_match=$(tofu workspace list | grep -w "$target" | tr -d '* ' || true)
    cd .. > /dev/null
    if [[ -n "$ws_match" ]]; then
        echo "$ws_match"
        return
    fi

    # 2. Check by IP
    if [[ "$target" =~ ^([0-9]{1,3}\.){3}[0-9]{1,3}$ ]]; then
        export GOVC_URL="$VCENTER_SERVER"
        export GOVC_USERNAME="$VCENTER_USERNAME"
        export GOVC_PASSWORD="$VCENTER_PASSWORD"
        export GOVC_INSECURE=true
        local ip_match=$(./build/govc vm.info -ip "$target" -json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['virtualMachines'][0]['name']) if 'virtualMachines' in data and data['virtualMachines'] else exit(1)" 2>/dev/null || true)
        if [[ -n "$ip_match" ]]; then
            echo "$ip_match"
            return
        fi
    fi

    # 3. Check by MAC
    if [[ "$target" =~ ^([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}$ ]]; then
        export GOVC_URL="$VCENTER_SERVER"
        export GOVC_USERNAME="$VCENTER_USERNAME"
        export GOVC_PASSWORD="$VCENTER_PASSWORD"
        export GOVC_INSECURE=true
        local mac_match=$(./build/govc vm.info -net.mac "$target" -json 2>/dev/null | python3 -c "import sys, json; data=json.load(sys.stdin); print(data['virtualMachines'][0]['name']) if 'virtualMachines' in data and data['virtualMachines'] else exit(1)" 2>/dev/null || true)
        if [[ -n "$mac_match" ]]; then
            echo "$mac_match"
            return
        fi
    fi

    # 4. Check for partial name match in workspaces
    cd tofu > /dev/null
    local part_match=$(tofu workspace list | grep "$target" | head -n 1 | tr -d '* ' || true)
    cd .. > /dev/null
    if [[ -n "$part_match" ]]; then
        echo "$part_match"
        return
    fi

    return 1
}

# Function to show comprehensive help
show_help() {
    echo "Unified HomeLab GitOps Orchestrator"
    echo "Usage: $0 [flags] {command} [profile] [id] [overrides]"
    echo ""
    echo "Core Commands:"
    echo "  build           Build a Golden OVF template via Packer (Photon only)"
    echo "  lint            Validate YAML profile and vCenter infrastructure objects"
    echo "  deploy          Provision virtual hardware via OpenTofu (Isolated Workspaces)"
    echo "  config          Apply configuration via Ansible (Auto-Limited by Profile/ID)"
    echo "  test            Run Pytest-Testinfra OS and service validation"
    echo "  destroy         Remove VM using single identifier (Name, IP, or MAC)"
    echo "  all             Full pipeline: Lint -> Deploy -> Config -> Test -> Destroy (unless -k)"
    echo ""
    echo "Generator Helpers:"
    echo "  create-profile  Interactive wizard to scaffold a new YAML configuration profile"
    echo "  edit-profile    Interactive wizard to update an existing profile"
    echo "  create-role     Interactive wizard to scaffold a new Ansible role"
    echo "  create-play     Interactive wizard to create a new targeting 'bucket' (play) in site.yml"
    echo ""
    echo "Options & Flags:"
    echo "  -h, --help           Show this help menu"
    echo "  -k, --keep           Skip 'destroy' phase at end of 'all' or explicit 'destroy'"
    echo ""
    echo "Runtime Overrides:"
    echo "  --host <name>        Override target ESXi host"
    echo "  --mac <addr>         Override network MAC address"
    echo "  --ip <addr>          Set static IPv4 (Enables Guest Customization)"
    echo "  --hostname <name>    Override VM hostname"
    echo "  --gateway <addr>     Set IPv4 gateway (Required for --ip)"
    echo "  --dns <addr>         Set DNS server (Default: 8.8.8.8)"
    echo ""
    echo "Automatic Filtering (Implied Limits):"
    echo "  Providing both Profile and ID (e.g. config ubuntu-base 04) limits Ansible to that single VM."
    echo "  Providing only a Profile (e.g. config ubuntu-base) limits Ansible to all VMs with that profile tag."
    echo ""
    echo "Examples:"
    echo "  1. Provision node with Static IP:"
    echo "     $0 deploy ubuntu-base 01 --ip 10.10.10.50 --gateway 10.10.10.1"
    echo ""
    echo "  2. Configure only a specific instance:"
    echo "     $0 config photon-docker 02"
    echo ""
    echo "  3. Simplified Destruction:"
    echo "     $0 destroy 10.10.10.118"
    echo ""
    echo "  4. Interactive Mode (Builder):"
    echo "     $0"
    exit 0
}

# Function for Interactive Mode
interactive_mode() {
    echo "--- HomeLab GitOps Command Builder ---"
    
    # 1. Pick Command
    PS3="Select Command: "
    options=("build" "lint" "deploy" "config" "test" "destroy" "all" "create-profile" "edit-profile" "create-role" "create-play" "Quit")
    select opt in "${options[@]}"; do
        case $opt in
            "Quit") exit 0 ;;
            *) I_COMMAND=$opt; break ;;
        esac
    done

    # Handle Generator Commands separately (no profile/id required)
    if [[ "$I_COMMAND" == "create-profile" || "$I_COMMAND" == "edit-profile" || "$I_COMMAND" == "create-role" || "$I_COMMAND" == "create-play" ]]; then
        $0 $I_COMMAND
        exit 0
    fi

    # Handle Destroy separately (only one identifier)
    if [[ "$I_COMMAND" == "destroy" ]]; then
        echo ""
        read -p "Enter VM Name, IP, or MAC to destroy: " I_ID
        if [[ -n "$I_ID" ]]; then
            $0 destroy "$I_ID"
        fi
        exit 0
    fi

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

# Load Consolidated Secrets (Fail-Fast if missing)
check_secrets
load_env "config/secrets.env"

# Export standard Ansible VMware vars
export VMWARE_HOST="$VCENTER_SERVER"
export VMWARE_USER="$VCENTER_USERNAME"
export VMWARE_PASSWORD="$VCENTER_PASSWORD"
export VMWARE_VALIDATE_CERTS="no"

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
        --limit) 
            echo "Warning: '--limit' is deprecated. Targeting is now automatic (Implied Limits)."
            echo "Hint: Pass Profile + ID for a single instance, or just Profile for a group."
            shift 
            ;;
        -*) 
            echo "Error: Unrecognized flag '$1'"
            echo "Hint: Use './manage.sh --help' to see all valid flags."
            exit 1 
            ;;
        *)
            if [[ -z "$COMMAND" ]]; then
                COMMAND="$1"
            elif [[ -z "$PROFILE" ]]; then
                PROFILE="$1"
                PROFILE_SET=true
            elif [[ -z "$INSTANCE_ID" ]]; then
                INSTANCE_ID="$1"
                INSTANCE_SET=true
            else
                echo "Error: Unexpected positional argument '$1'"
                echo "Hint: Correct usage is './manage.sh [flags] command profile id'"
                exit 1
            fi
            ;;
    esac
    shift
done

# Validate required positional arguments
if [[ -z "$COMMAND" ]]; then show_help; fi

# Set defaults for profile/id (for commands that need them)
if [[ "$COMMAND" != "build" && "$COMMAND" != "config" && "$COMMAND" != "lint" && "$COMMAND" != "create-profile" && "$COMMAND" != "edit-profile" && "$COMMAND" != "create-role" && "$COMMAND" != "create-play" && "$COMMAND" != "destroy" ]]; then
    PROFILE=${PROFILE:-"photon-docker"}
    INSTANCE_ID=${INSTANCE_ID:-"01"}
fi

validate_mac "$MAC_OVERRIDE"

# Load profile data for Name construction (if profile provided)
if [[ -n "$PROFILE" && -f "config/profiles/${PROFILE}.yml" ]]; then
    eval $(python3 -c "import yaml; c=yaml.safe_load(open('config/profiles/${PROFILE}.yml')); \
        print(f'VM_PREFIX=\"{c[\"deployment\"][\"vm_name_prefix\"]}\"'); \
        print(f'VM_DOMAIN=\"{c[\"deployment\"][\"vm_name_domain\"]}\"');")
    
    if [[ -n "$HOSTNAME_OVERRIDE" ]]; then
        VM_NAME="${HOSTNAME_OVERRIDE}.${VM_DOMAIN}"
    else
        VM_NAME="${VM_PREFIX}-${INSTANCE_ID:-"01"}.${VM_DOMAIN}"
    fi
fi

# ==========================================================
# 3. COMMAND EXECUTION
# ==========================================================

case $COMMAND in
    create-profile)
        python3 scripts/profile_manager.py create
        ;;

    edit-profile)
        python3 scripts/profile_manager.py edit
        ;;

    create-role)
        python3 scripts/role_manager.py
        ;;

    create-play)
        python3 scripts/play_manager.py
        ;;

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
        
        # Implied Limits Logic
        if [[ -n "$INSTANCE_SET" ]]; then
            LIMIT_ARG="-l $VM_NAME"
            echo "Auto-Filter: Instance ($VM_NAME)"
        elif [[ -n "$PROFILE_SET" ]]; then
            # Extract the first tag from the profile YAML
            PRIMARY_TAG=$(python3 -c "import yaml; c=yaml.safe_load(open('config/profiles/${PROFILE}.yml')); print(c['deployment']['tags'][0])")
            LIMIT_ARG="-l tag_$PRIMARY_TAG"
            echo "Auto-Filter: Profile group (tag_$PRIMARY_TAG)"
        else
            LIMIT_ARG=""
            echo "Auto-Filter: None (Broad Deployment)"
        fi
        
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
        
        # Identification Logic
        # For destroy, the identifier might be in PROFILE (if used as ./manage.sh destroy 10.10.10.x)
        TARGET_ID="${PROFILE:-$INSTANCE_ID}"
        if [[ -z "$TARGET_ID" ]]; then
            echo "Error: 'destroy' requires an identifier (Name, IP, or MAC)."
            echo "Example: ./manage.sh destroy 10.10.10.50"
            exit 1
        fi

        echo "Identifying VM for destruction: $TARGET_ID..."
        RESOLVED_NAME=$(identify_vm "$TARGET_ID")
        if [[ $? -ne 0 ]] || [[ -z "$RESOLVED_NAME" ]]; then
            echo "Error: Could not identify a managed VM matching '$TARGET_ID'."
            exit 1
        fi

        # Confirmation Prompt
        echo ""
        read -p "WARNING: Are you sure you want to permanently destroy '$RESOLVED_NAME'? (y/N): " CONFIRM
        if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
            echo "Destruction cancelled."
            exit 0
        fi

        echo "Destroying Workspace: $RESOLVED_NAME"
        cd tofu
        tofu workspace select "$RESOLVED_NAME" || exit 1
        tofu destroy -auto-approve \
            -var="vcenter_server=$VCENTER_SERVER" \
            -var="vcenter_user=$VCENTER_USERNAME" \
            -var="vcenter_password=$VCENTER_PASSWORD" \
            -var="datacenter=x" -var="cluster=x" -var="host=x" -var="datastore=x" -var="network=x" \
            -var="vm_name=$RESOLVED_NAME" -var="vm_cpu=1" -var="vm_ram_gb=1" \
            -var="guest_id=x" -var="library_name=x" -var="template_name=x" -var="vm_tags=x"
        tofu workspace select default
        tofu workspace delete "$RESOLVED_NAME"
        cd ..
        track_time $START $(date +%s) "Destruction"
        ;;

    all)
        TOTAL_START=$(date +%s)
        $0 lint $PROFILE $INSTANCE_ID --host "$TARGET_HOST"
        $0 deploy $PROFILE $INSTANCE_ID --host "$TARGET_HOST" --mac "$MAC_OVERRIDE" --ip "$IP_OVERRIDE" --hostname "$HOSTNAME_OVERRIDE" --netmask "$NETMASK" --gateway "$GATEWAY" --dns "$DNS"
        $0 config $PROFILE $INSTANCE_ID
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
