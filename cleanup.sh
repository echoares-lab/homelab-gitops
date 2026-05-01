#!/bin/bash
# Automated cleanup for test folders using govc

# Configuration
TEST_FOLDERS=("Builds/Linux/Ubuntu/Test" "Deploy/Linux/Ubuntu/Test")
RETENTION_HOURS=1
FORCE_PURGE=false

# Parse arguments
while [[ "$#" -gt 0 ]]; do
    case $1 in
        -f|--force) FORCE_PURGE=true ;;
        *) echo "Unknown parameter passed: $1"; exit 1 ;;
    esac
    shift
done

# Ensure GOVC_URL/USER/PASS are set (loaded from environment if run via wrapper)
# We assume they are exported in the environment.

for folder in "${TEST_FOLDERS[@]}"; do
    echo "Processing folder: $folder"
    
    items=$(govc ls "$folder" 2>/dev/null)
    
    if [ -z "$items" ]; then
        echo "No items found in $folder."
        continue
    fi
    
    for item in $items; do
        item_name=$(basename "$item")
        
        # Get creation time
        creation_time=$(govc object.collect -s "$item" config.createDate | awk '{print $2, $3}')
        
        # Calculate age
        item_date=$(date -d "$creation_time" +%s)
        now=$(date +%s)
        age_hours=$(( (now - item_date) / 3600 ))
        
        echo "Item: $item_name (Age: $age_hours hours)"
        
        if [ "$FORCE_PURGE" = true ] || [ "$age_hours" -ge "$RETENTION_HOURS" ]; then
            echo "Destroying $item_name..."
            govc vm.destroy "$item"
        else
            echo "Skipping $item_name (under retention threshold)."
        fi
    done
done
