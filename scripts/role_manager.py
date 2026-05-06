import os
import sys
import yaml
import re

ROLES_DIR = "ansible/roles"
SITE_YML = "ansible/site.yml"
STANDARDS_GUIDANCE = """
--- ROLE NAMING STANDARDS ---
1. Use lowercase alphanumeric characters and underscores ONLY.
2. No hyphens, spaces, or special characters.
3. Examples: 'install_nginx', 'harden_ssh', 'configure_ufw'.
-----------------------------
"""

def validate_role_name(name):
    if not re.match(r"^[a-z0-9_]+$", name):
        print(f"Error: Invalid name '{name}'. Roles must be lowercase and use underscores only.")
        return False
    return True

def create_role():
    print(STANDARDS_GUIDANCE)
    name = input("Enter new role name: ").strip()
    if not validate_role_name(name):
        return

    role_path = os.path.join(ROLES_DIR, name)
    if os.path.exists(role_path):
        print(f"Error: Role '{name}' already exists.")
        return

    # Scaffold directories
    subdirs = ["tasks", "handlers", "defaults", "vars", "templates", "files", "meta"]
    for sd in subdirs:
        os.makedirs(os.path.join(role_path, sd), exist_ok=True)
        # Create empty main.yml in relevant dirs
        if sd in ["tasks", "handlers", "defaults", "vars"]:
            with open(os.path.join(role_path, sd, "main.yml"), "w") as f:
                f.write("---\n# main.yml for role: " + name + "\n")

    print(f"Successfully scaffolded role at: {role_path}")

    # Attach to site.yml
    attach = input("Would you like to attach this role to existing plays in site.yml? (y/N): ")
    if attach.lower() == 'y':
        with open(SITE_YML, 'r') as f:
            site = yaml.safe_load(f)

        print("\nAvailable Plays in site.yml:")
        active_plays = [p for p in site if "hosts" in p and p["hosts"] != "all"]
        for i, play in enumerate(active_plays):
            print(f"{i+1}) {play.get('name', 'Unnamed Play')} (targets: {play['hosts']})")

        choices = input(f"Select play(s) to attach to (comma separated, 1-{len(active_plays)}): ")
        try:
            indices = [int(x.strip()) - 1 for x in choices.split(",")]
            for idx in indices:
                play = active_plays[idx]
                if "roles" not in play:
                    play["roles"] = []
                if name not in play["roles"]:
                    play["roles"].append(name)
                    print(f"Added role '{name}' to play: {play.get('name')}")
            
            with open(SITE_YML, 'w') as f:
                yaml.dump(site, f, default_flow_style=False, sort_keys=False)
        except (ValueError, IndexError):
            print("Invalid selection. Skipping attachment.")

if __name__ == "__main__":
    create_role()
