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


def bao_put(path, data):
    body = json.dumps({"data": data}).encode()
    req = urllib.request.Request(
        f"{BAO}/v1/kv/data/{path}",
        data=body,
        headers={"X-Vault-Token": ROOT_TOKEN, "Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req) as r:
        resp = json.load(r)
    print(f"  wrote kv/data/{path} -> version {resp['data']['version']}")


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
bao_put("prod/platform/truenas",    {"TRUENAS_API_KEY":      truenas_key})
bao_put("prod/platform/technitium", {"TECHNITIUM_TSIG_KEY":  technitium})
bao_put("prod/platform/cloudflare", {"CLOUDFLARE_API_TOKEN": cloudflare})

print("")
print("=== Step 3: Verify paths readable ===")
for path in ("prod/platform/truenas", "prod/platform/technitium", "prod/platform/cloudflare"):
    resp = bao_read(path)
    if resp:
        keys = list(resp["data"]["data"].keys())
        print(f"  {path}: {keys}")
    else:
        print(f"  {path}: NOT FOUND (write may have failed)")

print("")
print("Done. Force ExternalSecret resync with:")
print("  ssh core@10.10.10.50 \"sudo k3s kubectl annotate externalsecret -A --all force-sync=$(date +%s) --overwrite\"")
