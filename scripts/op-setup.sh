#!/usr/bin/env bash
# scripts/op-setup.sh
# Validates all required 1Password vault items and fields exist.
# When a field is missing it prompts for the value and uploads it.
#
# Usage:
#   export OP_SERVICE_ACCOUNT_TOKEN="ops_..."
#   bash scripts/op-setup.sh

set -euo pipefail

VAULT="Homelab-GitOps"
SECRETS_ENV="config/secrets.env"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

pass()    { echo -e "  ${GREEN}✓${RESET} $1"; }
fail()    { echo -e "  ${RED}✗${RESET} $1"; ERRORS=$((ERRORS+1)); }
info()    { echo -e "  ${CYAN}→${RESET} $1"; }
warn()    { echo -e "  ${YELLOW}!${RESET} $1"; }
section() { echo -e "\n  ${BOLD}${CYAN}── $1 ──${RESET}"; }

ERRORS=0

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   1Password Setup Validator              ║${RESET}"
echo -e "${BOLD}║   homelab-gitops / Homelab-GitOps vault  ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── 1. Check op CLI ───────────────────────────────────────────────────────────
echo -e "${BOLD}[1/5] Checking 1Password CLI${RESET}"
if command -v op &>/dev/null; then
    OP_VER=$(op --version 2>/dev/null || echo "unknown")
    pass "op CLI installed (v${OP_VER})"
else
    fail "op CLI not found"
    info "Run: bash scripts/op-vault-setup.sh  (installs the CLI and fills the vault)"
    exit 1
fi

# ── 2. Check service account token ───────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/5] Checking OP_SERVICE_ACCOUNT_TOKEN${RESET}"
if [[ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
    fail "OP_SERVICE_ACCOUNT_TOKEN is not set"
    info "1Password → Settings → Developer → Service Accounts → create one scoped to '${VAULT}'"
    info "Then: export OP_SERVICE_ACCOUNT_TOKEN='ops_...'"
    exit 1
else
    pass "OP_SERVICE_ACCOUNT_TOKEN is set"
fi

# ── 3. Test authentication ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[3/5] Testing 1Password authentication${RESET}"
if op vault list --format=json &>/dev/null; then
    pass "Authentication successful"
    if op vault get "${VAULT}" &>/dev/null; then
        pass "Vault '${VAULT}' is accessible"
    else
        fail "Vault '${VAULT}' not found or not accessible"
        info "Create the vault in 1Password UI and grant the service account read+write access."
        exit 1
    fi
else
    fail "Authentication failed — check OP_SERVICE_ACCOUNT_TOKEN value"
    exit 1
fi

# ── Helpers ───────────────────────────────────────────────────────────────────

# Upload a single field to an existing item, or create the item if it doesn't exist.
# Usage: _upload item field field_type category value
_upload() {
    local item="$1" field="$2" field_type="$3" category="$4" value="$5"

    if op item get "$item" --vault "$VAULT" &>/dev/null; then
        op item edit "$item" --vault "$VAULT" \
            "${field}[${field_type}]=${value}" --format json >/dev/null \
            || { fail "${item}/${field} — upload failed"; return 0; }
    else
        op item create --category "$category" --title "$item" --vault "$VAULT" \
            "${field}[${field_type}]=${value}" --format json >/dev/null \
            || { fail "${item}/${field} — create failed"; return 0; }
    fi
    pass "${item}/${field} — uploaded"
}

# Check a field; prompt and upload if missing.
# Usage: check_field item field [field_type] [category]
#   field_type: text (default) | password | concealed
#   category:   Login (default) | Secure Note
check_field() {
    local item="$1" field="$2" field_type="${3:-text}" category="${4:-Login}"
    local ref="op://${VAULT}/${item}/${field}"

    if val=$(op read "${ref}" 2>/dev/null) && [[ -n "$val" ]]; then
        pass "${item}/${field}"
        return 0
    fi

    # Missing — prompt for value
    warn "${item}/${field} is missing"
    local new_val
    if [[ "$field_type" == "password" || "$field_type" == "concealed" ]]; then
        read -rsp "$(echo -e "    ${YELLOW}Enter value${RESET} ${DIM}(hidden)${RESET}: ")" new_val
        echo ""
    else
        read -rp "$(echo -e "    ${YELLOW}Enter value${RESET}: ")" new_val
    fi

    if [[ -z "$new_val" ]]; then
        fail "${item}/${field} — skipped (left blank)"
        return 0
    fi

    _upload "$item" "$field" "$field_type" "$category" "$new_val"
}

# ── 4. Check all required items and fields ───────────────────────────────────
echo ""
echo -e "${BOLD}[4/5] Checking vault items and fields${RESET}"

section "vCenter"
check_field "vCenter" "server"         text     Login
check_field "vCenter" "username"       text     Login
check_field "vCenter" "password"       password Login
check_field "vCenter" "datacenter"     text     Login
check_field "vCenter" "cluster"        text     Login
check_field "vCenter" "datastore"      text     Login
check_field "vCenter" "network"        text     Login
check_field "vCenter" "build_folder"       text Login
check_field "vCenter" "template_folder"    text Login
check_field "vCenter" "build_test_folder"  text Login
check_field "vCenter" "deploy_prod_folder" text Login
check_field "vCenter" "deploy_test_folder" text Login

section "SSH-Admin"
check_field "SSH-Admin" "username" text     Login
check_field "SSH-Admin" "password" password Login
check_field "SSH-Admin" "pubkey"   text     Login
check_field "SSH-Admin" "key_path" text     Login

section "Content-Library"
check_field "Content-Library" "name"      text "Secure Note"
check_field "Content-Library" "item_name" text "Secure Note"

section "Build-ISOs"
check_field "Build-ISOs" "ubuntu_2404_iso_url"      text "Secure Note"
check_field "Build-ISOs" "ubuntu_2404_iso_checksum" text "Secure Note"
check_field "Build-ISOs" "ubuntu_2604_iso_url"      text "Secure Note"
check_field "Build-ISOs" "ubuntu_2604_iso_checksum" text "Secure Note"
check_field "Build-ISOs" "photon_iso_url"            text "Secure Note"
check_field "Build-ISOs" "photon_iso_checksum"       text "Secure Note"

section "Build-Config"
check_field "Build-Config" "packer_firmware"     text "Secure Note"
check_field "Build-Config" "template_cpu_count"  text "Secure Note"
check_field "Build-Config" "template_memory_mb"  text "Secure Note"
check_field "Build-Config" "template_disk_size_mb" text "Secure Note"

section "GitHub"
check_field "GitHub" "github_pat" password Login

section "Technitium"
check_field "Technitium" "host"  text     Login
check_field "Technitium" "token" password Login

# ── 5. Validate secrets.env resolves ─────────────────────────────────────────
echo ""
echo -e "${BOLD}[5/5] Validating secrets.env resolves via op run${RESET}"
if [[ -f "${SECRETS_ENV}" ]]; then
    if op run --env-file="${SECRETS_ENV}" -- env 2>/dev/null | grep -q "VCENTER_SERVER"; then
        pass "secrets.env resolves correctly"
        VC=$(op run --env-file="${SECRETS_ENV}" -- sh -c 'echo "${VCENTER_SERVER}"' 2>/dev/null)
        info "VCENTER_SERVER = ${VC}"
    else
        fail "secrets.env did not inject VCENTER_SERVER"
    fi
else
    fail "${SECRETS_ENV} not found"
fi

# ── Summary ───────────────────────────────────────────────────────────────────
echo ""
if [[ $ERRORS -eq 0 ]]; then
    echo -e "${GREEN}${BOLD}All checks passed! Ready to use 1Password secrets.${RESET}"
    echo ""
    echo -e "  ${BOLD}Run manage.py:${RESET}"
    echo -e "  ${CYAN}python3 manage.py deploy ubuntu-2404-base 01${RESET}"
    echo ""
else
    echo -e "${RED}${BOLD}${ERRORS} check(s) failed.${RESET}"
    echo ""
    echo -e "  Reference vault structure: ${CYAN}config/vault.yml.example${RESET}"
    exit 1
fi
