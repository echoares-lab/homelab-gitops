#!/usr/bin/env python3
"""Seed OpenBao KV store from 1Password secrets."""
import json
import os
import subprocess
import sys
import urllib.request

ROOT_TOKEN = os.environ.get("ROOT_TOKEN", "")
if not ROOT_TOKEN:
    print("ERROR: ROOT_TOKEN is not set.")
    print("  export ROOT_TOKEN=$(op document get affyyquvnukbgq76zj2s62ndxm --vault Homelab-GitOps | python3 -c \"import json,sys; print(json.load(sys.stdin)['root_token'])\")")
    sys.exit(1)

BAO = "http://10.10.10.30:8201"


def op_field(item_id, field_label, vault=None):
    cmd = ["op", "item", "get", item_id, "--format", "json"]
    if vault:
        cmd += ["--vault", vault]
    d = json.loads(subprocess.check_output(cmd))
    for f in d.get("fields", []):
        if f.get("label") == field_label:
            return f["value"]
    raise KeyError(f"field {field_label!r} not found in item {item_id}")


LEGACY_PREFIXES = ("prod/", "staging/", "repo/", "workloads/")


def _reject_legacy(path):
    """Refuse to write a legacy path.

    Epic 2 moved every consumer to kv/data/agents/... and Epic 3 will prune the
    legacy tree. This script writes with a ROOT token, so a single run against
    the old paths would silently recreate them after the prune and leave the
    estate with two live copies of three credentials. Failing loudly is the only
    safe behaviour: a seeding script is exactly the thing someone re-runs a year
    later without reading it.
    """
    if path.startswith(LEGACY_PREFIXES):
        raise SystemExit(
            f"REFUSING to write legacy path kv/data/{path}.\n"
            "  The agent-scoped taxonomy is authoritative (Secrets-Policy 2.1) and the\n"
            "  legacy tree is scheduled for pruning. Writing here would resurrect it.\n"
            "  Use kv/data/agents/{agent_type}/{agent_id}/{environment}."
        )


def bao_merge(path, data):
    """Merge keys into a secret, preserving every key already there.

    Deliberately NOT a plain put. The KV-v2 write endpoint REPLACES the whole
    payload, and the agent-scoped destinations are shared: cloudflare-platform
    holds 5 keys and truenas-storage holds 14 (TrueNAS + TrueNAS-S3 + MinIO,
    consolidated by the 2026-08-11 dual-write). A replace-style write of the one
    key this script owns would delete the siblings and take down cert-manager,
    alertmanager, the breakglass SES watchdog, democratic-csi and the postgres
    backups simultaneously.
    """
    _reject_legacy(path)
    existing = bao_read(path)
    merged = dict(existing["data"]["data"]) if existing else {}
    untouched = sorted(k for k in merged if k not in data)
    merged.update(data)

    body = json.dumps({"data": merged}).encode()
    req = urllib.request.Request(
        f"{BAO}/v1/kv/data/{path}",
        data=body,
        headers={"X-Vault-Token": ROOT_TOKEN, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        resp = json.load(r)
    print(f"  merged kv/data/{path} -> version {resp['data']['version']} "
          f"(set: {sorted(data)}; preserved {len(untouched)}: {untouched})")


def bao_read(path):
    req = urllib.request.Request(
        f"{BAO}/v1/kv/data/{path}",
        headers={"X-Vault-Token": ROOT_TOKEN},
    )
    try:
        with urllib.request.urlopen(req) as r:
            return json.load(r)
    except urllib.error.HTTPError:
        return None


print("=== Step 1: Fetch secrets from 1Password ===")
truenas_key = op_field("nsv323wxayulqtwtek36ktiubi", "api_key",               vault="Homelab-GitOps")
technitium  = op_field("mbyxafapjd2kmbdahxli6abz4y", "token",                vault="Homelab-GitOps")
cloudflare  = op_field("ykx2u5rfpcnvpfogptyglgqdga", "CLOUDFLARE_API_TOKEN",  vault="platform-cloudflare")
print("  fetched: truenas api_key, technitium token, cloudflare api token")

print("")
print("=== Step 2: Write to OpenBao KV ===")
bao_merge("agents/autonomous/truenas-storage/prod",    {"TRUENAS_API_KEY":      truenas_key})
bao_merge("agents/autonomous/technitium-dns/prod",     {"TECHNITIUM_TSIG_KEY":  technitium})
bao_merge("agents/autonomous/cloudflare-platform/prod", {"CLOUDFLARE_API_TOKEN": cloudflare})

print("")
print("=== Step 3: Verify paths readable ===")
for path in ("agents/autonomous/truenas-storage/prod",
             "agents/autonomous/technitium-dns/prod",
             "agents/autonomous/cloudflare-platform/prod"):
    resp = bao_read(path)
    if resp:
        keys = list(resp["data"]["data"].keys())
        print(f"  {path}: {keys}")
    else:
        print(f"  {path}: NOT FOUND (write may have failed)")

print("")
print("Done. Force ExternalSecret resync with:")
print("  ssh core@10.10.10.50 \"sudo k3s kubectl annotate externalsecret -A --all force-sync=$(date +%s) --overwrite\"")
