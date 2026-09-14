#!/usr/bin/env python3
"""
Sync Jellyfin Approved Device Fingerprints to Cloudflare WAF.
Reads config/jellyfin_approved_devices.yaml and updates the Cloudflare custom ruleset.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

CONFIG_FILE = Path(__file__).resolve().parent.parent / "config" / "jellyfin_approved_devices.yaml"
RULESET_PHASE = "http_request_firewall_custom"
RULE_DESCRIPTION = "Jellyfin Device Enforcement: Restrict API and Auth to Approved Device IDs"


def get_cloudflare_token() -> str:
    """Retrieve Cloudflare API token from OpenBao."""
    try:
        res = subprocess.run(
            ["bao", "kv", "get", "-format=json", "kv/agents/autonomous/cloudflare-platform/prod"],
            capture_output=True,
            text=True,
            check=True,
        )
        data = json.loads(res.stdout)
        token = data["data"]["data"].get("CLOUDFLARE_API_TOKEN")
        if not token:
            raise ValueError("CLOUDFLARE_API_TOKEN key not found in OpenBao secret payload")
        return token
    except Exception as err:
        print(f"Error fetching Cloudflare token from OpenBao: {err}", file=sys.stderr)
        sys.exit(1)


def get_zone_id(token: str, zone_name: str = "plexplease.com") -> str:
    """Retrieve Zone ID for domain."""
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones?name={zone_name}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        results = data.get("result", [])
        if not results:
            raise ValueError(f"Zone {zone_name} not found in Cloudflare account")
        return results[0]["id"]


def load_devices() -> list[dict[str, Any]]:
    """Load authorized devices from YAML."""
    import yaml

    if not CONFIG_FILE.exists():
        print(f"Config file {CONFIG_FILE} not found.", file=sys.stderr)
        sys.exit(1)

    with open(CONFIG_FILE, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    return data.get("devices", [])


def build_waf_expression(devices: list[dict[str, Any]]) -> str:
    """Construct Cloudflare WAF Expression matching approved device IDs."""
    enabled_devices = [d for d in devices if d.get("enabled", True) and d.get("device_id")]
    if not enabled_devices:
        raise ValueError("No enabled devices with valid device_id found in config")

    device_conditions = []
    for d in enabled_devices:
        device_id = d["device_id"].replace('"', '\\"')
        device_conditions.append(
            f'any(http.request.headers["x-emby-authorization"][*] contains "{device_id}")'
        )

    matched_devices = "\n        or ".join(device_conditions)

    expression = (
        'http.host eq "jellyfin.plexplease.com"\n'
        '  and (\n'
        '    starts_with(http.request.uri.path, "/Users/")\n'
        '    or starts_with(http.request.uri.path, "/Sessions/")\n'
        '    or starts_with(http.request.uri.path, "/Items/")\n'
        '    or starts_with(http.request.uri.path, "/QuickConnect/")\n'
        '  )\n'
        '  and not (\n'
        f'    {matched_devices}\n'
        '  )'
    )
    return expression


def get_custom_ruleset(token: str, zone_id: str) -> dict[str, Any]:
    """Find the custom firewall ruleset."""
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode())
        for r in data.get("result", []):
            if r.get("phase") == RULESET_PHASE:
                return r
    raise ValueError(f"No ruleset found in phase {RULESET_PHASE}")


def sync_ruleset(token: str, zone_id: str, dry_run: bool = False) -> None:
    """Sync the device rule into Cloudflare WAF ruleset."""
    devices = load_devices()
    expression = build_waf_expression(devices)

    print("=== Generated Cloudflare WAF Rule Expression ===")
    print(expression)
    print("=================================================")

    if dry_run:
        print("\n[Dry Run] Changes not applied to Cloudflare.")
        return

    ruleset_meta = get_custom_ruleset(token, zone_id)
    ruleset_id = ruleset_meta["id"]

    # Fetch full ruleset details
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets/{ruleset_id}",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req) as resp:
        full_ruleset = json.loads(resp.read().decode())["result"]

    rules = full_ruleset.get("rules", [])
    existing_rule_index = None
    for idx, rule in enumerate(rules):
        if rule.get("description") == RULE_DESCRIPTION:
            existing_rule_index = idx
            break

    target_rule = {
        "action": "block",
        "description": RULE_DESCRIPTION,
        "enabled": True,
        "expression": expression,
    }

    if existing_rule_index is not None:
        target_rule["id"] = rules[existing_rule_index]["id"]
        rules[existing_rule_index] = target_rule
        print(f"Updating existing rule '{RULE_DESCRIPTION}' (ID: {target_rule['id']})")
    else:
        rules.append(target_rule)
        print(f"Adding new rule '{RULE_DESCRIPTION}' to ruleset {ruleset_id}")

    # Update ruleset
    update_payload = json.dumps({"rules": rules}).encode("utf-8")
    req = urllib.request.Request(
        f"https://api.cloudflare.com/client/v4/zones/{zone_id}/rulesets/{ruleset_id}",
        data=update_payload,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
        method="PUT",
    )

    try:
        with urllib.request.urlopen(req) as resp:
            res_data = json.loads(resp.read().decode())
            if res_data.get("success"):
                print(" Successfully synced approved Jellyfin device fingerprints to Cloudflare WAF!")
            else:
                print(f" Cloudflare update failed: {res_data.get('errors')}", file=sys.stderr)
                sys.exit(1)
    except urllib.error.HTTPError as err:
        err_msg = err.read().decode()
        print(f" HTTP {err.code} Error updating Cloudflare: {err_msg}", file=sys.stderr)
        sys.exit(1)


def list_devices() -> None:
    """Print the list of configured devices."""
    devices = load_devices()
    print(f"=== Authorized Jellyfin Devices ({len(devices)} total) ===")
    for d in devices:
        status = " Enabled" if d.get("enabled", True) else " Disabled"
        print(f"- [{status}] User: {d.get('user')} | Device: {d.get('device_name')} ({d.get('client')})")
        print(f"  Device ID: {d.get('device_id')}")
        if d.get("notes"):
            print(f"  Notes: {d.get('notes')}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Jellyfin Cloudflare WAF Device Sync CLI")
    parser.add_argument("--sync", action="store_true", help="Sync YAML device list to Cloudflare WAF")
    parser.add_argument("--dry-run", action="store_true", help="Print WAF expression without applying")
    parser.add_argument("--list", action="store_true", help="List registered devices")

    args = parser.parse_args()

    if args.list:
        list_devices()
        return

    if args.sync or args.dry_run:
        token = get_cloudflare_token()
        zone_id = get_zone_id(token)
        sync_ruleset(token, zone_id, dry_run=args.dry_run)
        return

    parser.print_help()


if __name__ == "__main__":
    main()
