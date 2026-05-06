import yaml
import os
import sys
import re

PROFILE_DIR = "config/profiles"
STANDARDS_GUIDANCE = """
--- PROFILE NAMING STANDARDS ---
1. Use lowercase alphanumeric characters and hyphens ONLY.
2. No underscores, spaces, or special characters.
3. Examples: 'ubuntu-base', 'db-cluster-high-mem'.
--------------------------------
"""

def validate_profile_name(name):
    if not re.match(r"^[a-z0-9-]+$", name):
        print(f"Error: Invalid name '{name}'. Profiles must be lowercase and use hyphens only.")
        return False
    return True

def create_profile():
    print(STANDARDS_GUIDANCE)
    name = input("Enter new profile name: ").strip()
    if not validate_profile_name(name):
        return

    file_path = os.path.join(PROFILE_DIR, f"{name}.yml")
    if os.path.exists(file_path):
        print(f"Error: Profile '{name}' already exists.")
        return

    # Gather inputs
    os_choice = input("Base OS (1 for Ubuntu, 2 for Photon) [1]: ") or "1"
    if os_choice == "2":
        guest_id = "vmwarePhoton64Guest"
        template = "photon-5.0-golden"
        prefix = "photon"
        tags = ["photon"]
    else:
        guest_id = "ubuntu64Guest"
        template = "ubuntu-26.04-golden"
        prefix = "ubuntu"
        tags = ["ubuntu"]

    cpu = int(input("CPU Count [2]: ") or 2)
    ram = int(input("RAM (GB) [8]: ") or 8)
    disk = int(input("Disk Size (GB) [50]: ") or 50)
    
    extra_tags = input(f"Extra Tags (comma separated) [none]: ").strip()
    if extra_tags:
        tags.extend([t.strip() for t in extra_tags.split(",")])

    # Construct Profile
    profile = {
        "vcenter": {
            "datacenter": "HOMELAB",
            "cluster": "Primary",
            "host": "esxi-01.mgmt.plexplease.com",
            "datastore": "NVME_2TB_970_SAMSUNG_EVO_M.2",
            "network": "VM Network"
        },
        "content_library": {
            "name": "GOLDEN",
            "template": template
        },
        "vm_specs": {
            "cpu": cpu,
            "ram_gb": ram,
            "guest_id": guest_id,
            "disk_size_gb": disk
        },
        "deployment": {
            "tags": tags,
            "vm_name_prefix": prefix,
            "vm_name_domain": "mgmt.plexplease.com"
        }
    }

    with open(file_path, 'w') as f:
        yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
    
    print(f"Successfully created profile: {file_path}")

def edit_profile():
    profiles = [p.replace(".yml", "") for p in os.listdir(PROFILE_DIR) if p.endswith(".yml")]
    if not profiles:
        print("No profiles found to edit.")
        return

    print("\nAvailable Profiles:")
    for i, p in enumerate(profiles):
        print(f"{i+1}) {p}")
    
    try:
        choice = int(input(f"Select profile to edit (1-{len(profiles)}): ")) - 1
        name = profiles[choice]
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    file_path = os.path.join(PROFILE_DIR, f"{name}.yml")
    with open(file_path, 'r') as f:
        profile = yaml.safe_load(f)

    print(f"\n--- Editing {name} ---")
    print("Press Enter to keep current value.")

    # Edit vcenter
    profile["vcenter"]["host"] = input(f"Target Host [{profile['vcenter']['host']}]: ") or profile["vcenter"]["host"]
    
    # Edit specs
    profile["vm_specs"]["cpu"] = int(input(f"CPU Count [{profile['vm_specs']['cpu']}]: ") or profile["vm_specs"]["cpu"])
    profile["vm_specs"]["ram_gb"] = int(input(f"RAM (GB) [{profile['vm_specs']['ram_gb']}]: ") or profile["vm_specs"]["ram_gb"])
    profile["vm_specs"]["disk_size_gb"] = int(input(f"Disk (GB) [{profile['vm_specs']['disk_size_gb']}]: ") or profile["vm_specs"]["disk_size_gb"])

    # Edit tags
    current_tags = ",".join(profile["deployment"]["tags"])
    new_tags = input(f"Tags [{current_tags}]: ")
    if new_tags:
        profile["deployment"]["tags"] = [t.strip() for t in new_tags.split(",")]

    with open(file_path, 'w') as f:
        yaml.dump(profile, f, default_flow_style=False, sort_keys=False)
    
    print(f"Successfully updated profile: {file_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: profile_manager.py {create|edit}")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "create":
        create_profile()
    elif cmd == "edit":
        edit_profile()
    else:
        print(f"Unknown command: {cmd}")
