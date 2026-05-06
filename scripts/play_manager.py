import os
import sys
import yaml
import re

SITE_YML = "ansible/site.yml"
ROLES_DIR = "ansible/roles"
STANDARDS_GUIDANCE = """
--- TAG NAMING STANDARDS ---
1. Use lowercase alphanumeric characters and underscores ONLY.
2. No hyphens, spaces, or special characters.
3. Examples: 'primary_dns', 'app_server', 'prod_db'.
-----------------------------
"""

def validate_tag_name(tag):
    if not re.match(r"^[a-z0-9_]+$", tag):
        print(f"Error: Invalid tag '{tag}'. Tags must be lowercase and use underscores only.")
        return False
    return True

def create_play():
    print(STANDARDS_GUIDANCE)
    
    play_name = input("Enter descriptive Play Name (e.g. Configure DNS Servers): ").strip()
    if not play_name:
        print("Error: Play name cannot be empty.")
        return

    tag = input("Enter target Tag (without 'tag_' prefix): ").strip()
    if not validate_tag_name(tag):
        return

    # 1. Get available roles
    roles = [r for r in os.listdir(ROLES_DIR) if os.path.isdir(os.path.join(ROLES_DIR, r))]
    if not roles:
        print("No roles found in ansible/roles/.")
        return

    print("\nAvailable Roles:")
    for i, r in enumerate(roles):
        print(f"{i+1}) {r}")

    choices = input(f"Select role(s) for this play (comma separated, 1-{len(roles)}): ")
    selected_roles = []
    try:
        indices = [int(x.strip()) - 1 for x in choices.split(",")]
        for idx in indices:
            selected_roles.append(roles[idx])
    except (ValueError, IndexError):
        print("Invalid selection.")
        return

    # 2. Construct Play
    new_play = {
        "name": play_name,
        "hosts": f"tag_{tag}",
        "become": True,
        "roles": selected_roles
    }

    # 3. Append to site.yml
    with open(SITE_YML, 'r') as f:
        site = yaml.safe_load(f)

    # site is a list of plays
    site.append(new_play)

    with open(SITE_YML, 'w') as f:
        # We use a custom dumper or ensure we don't destroy comments if possible
        # But yaml.dump is standard for now.
        yaml.dump(site, f, default_flow_style=False, sort_keys=False)

    print(f"\nSuccessfully added new play '{play_name}' targeting 'tag_{tag}' to {SITE_YML}")

if __name__ == "__main__":
    create_play()
