#!/bin/bash
set -e

# Function to load env files safely and export variables
load_env() {
    local env_file=$1
    if [ -f "$env_file" ]; then
        while IFS= read -r line || [[ -n "$line" ]]; do
            # Skip comments and empty lines
            [[ "$line" =~ ^#.*$ ]] && continue
            [[ -z "$line" ]] && continue
            
            # Extract key and value, then strip trailing comments from value
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

COMMAND=$1
VM_NAME=${2:-"photon-node-01"}

case $COMMAND in
    lint)
        START=$(date +%s)
        echo "Starting Configuration Linting..."
        python3 scripts/lint_config.py
        track_time $START $(date +%s) "Linting"
        ;;
    build)
        START=$(date +%s)
        echo "Starting Packer Build..."
        cd packer
        packer init .
        packer build -force -var "vcenter_password=$VCENTER_PASSWORD" photon.pkr.hcl
        cd ..
        track_time $START $(date +%s) "Packer Build"
        ;;
    deploy)
        START=$(date +%s)
        echo "Starting Advanced OpenTofu Deployment..."
        
        # Extract variables from YAML using a robust JSON output
        eval $(python3 -c "import yaml, json; c=yaml.safe_load(open('config/deploy.yml')); \
            print(f'export TF_VAR_datacenter=\"{c[\"vcenter\"][\"datacenter\"]}\"'); \
            print(f'export TF_VAR_cluster=\"{c[\"vcenter\"][\"cluster\"]}\"'); \
            print(f'export TF_VAR_datastore=\"{c[\"vcenter\"][\"datastore\"]}\"'); \
            print(f'export TF_VAR_network=\"{c[\"vcenter\"][\"network\"]}\"'); \
            print(f'export TF_VAR_vm_cpu=\"{c[\"vm_specs\"][\"cpu\"]}\"'); \
            print(f'export TF_VAR_vm_ram_gb=\"{c[\"vm_specs\"][\"ram_gb\"]}\"'); \
            print(f'export TF_VAR_library_name=\"{c[\"content_library\"][\"name\"]}\"'); \
            print(f'export TF_VAR_template_name=\"{c[\"content_library\"][\"template\"]}\"'); \
            print(f'export TF_VAR_mac_address=\"{c[\"deployment\"].get(\"mac_address\", \"\")}\"'); \
            print(f'export VM_PREFIX=\"{c[\"deployment\"][\"vm_name_prefix\"]}\"'); \
            print(f'export VM_INSTANCE=\"{c[\"deployment\"].get(\"vm_instance\", \"01\")}\"'); \
            print(f'export VM_DOMAIN=\"{c[\"deployment\"][\"vm_name_domain\"]}\"');")

        export TF_VAR_vcenter_server="$VCENTER_SERVER"
        export TF_VAR_vcenter_user="$VCENTER_USERNAME"
        export TF_VAR_vcenter_password="$VCENTER_PASSWORD"

        # Construct dynamic name if default node-01 is used or if explicitly requested
        if [ "$VM_NAME" == "photon-node-01" ]; then
            VM_NAME="${VM_PREFIX}-${VM_INSTANCE}.${VM_DOMAIN}"
        fi
        export TF_VAR_vm_name="$VM_NAME"
        echo "Deploying VM: $VM_NAME"

        cd tofu
        tofu init
        tofu apply -auto-approve
        
        VM_IP=$(tofu output -raw vm_ip)
        echo "VM Deployed at $VM_IP"
        echo "photon-node ansible_host=$VM_IP ansible_user=$SSH_ADMIN_USERNAME" > ../ansible/inventory.ini
        cd ..
        track_time $START $(date +%s) "Deployment"
        ;;
    config)
        START=$(date +%s)
        echo "Starting Ansible Configuration..."
        cd ansible
        export ANSIBLE_HOST_KEY_CHECKING=False
        ansible-playbook -i inventory.ini site.yml --extra-vars "ansible_ssh_pass=$SSH_ADMIN_PASSWORD" --ssh-extra-args='-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
        cd ..
        track_time $START $(date +%s) "Ansible Configuration"
        ;;
    all)
        TOTAL_START=$(date +%s)
        $0 lint
        $0 deploy $VM_NAME
        $0 config
        track_time $TOTAL_START $(date +%s) "TOTAL PIPELINE"
        ;;
    *)
        echo "Usage: $0 {build|deploy|config|all} [vm_name]"
        exit 1
        ;;
esac
