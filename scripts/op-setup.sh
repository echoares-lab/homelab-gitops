#!/usr/bin/env bash
# scripts/op-setup.sh
# Validates that 1Password CLI is installed, the service account token works,
# and all required items/fields exist in the Homelab-GitOps vault.
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
RESET='\033[0m'

pass() { echo -e "  ${GREEN}✓${RESET} $1"; }
fail() { echo -e "  ${RED}✗${RESET} $1"; ERRORS=$((ERRORS+1)); }
info() { echo -e "  ${CYAN}→${RESET} $1"; }

ERRORS=0

echo ""
echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
echo -e "${BOLD}║   1Password Setup Validator              ║${RESET}"
echo -e "${BOLD}║   homelab-gitops / Homelab-GitOps vault  ║${RESET}"
echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"
echo ""

# ── 1. Check op CLI ───────────────────────────────────────────────────────────
echo -e "${BOLD}[1/4] Checking 1Password CLI${RESET}"
if command -v op &>/dev/null; then
    OP_VER=$(op --version 2>/dev/null || echo "unknown")
    pass "op CLI installed (v${OP_VER})"
else
    fail "op CLI not found"
    echo ""
    info "Install via: https://developer.1password.com/docs/cli/get-started/"
    info "  Ubuntu/Debian: curl -sS https://downloads.1password.com/linux/keys/1password.asc | sudo gpg --dearmor -o /usr/share/keyrings/1password-archive-keyring.gpg"
    info "  Then add apt repo and: sudo apt install 1password-cli"
    exit 1
fi

# ── 2. Check service account token ───────────────────────────────────────────
echo ""
echo -e "${BOLD}[2/4] Checking OP_SERVICE_ACCOUNT_TOKEN${RESET}"
if [[ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
    fail "OP_SERVICE_ACCOUNT_TOKEN is not set"
    echo ""
    info "Create a service account:"
    info "  1. Open 1Password → Settings → Developer → Service Accounts"
    info "  2. Create new account scoped to '${VAULT}' vault (read-only)"
    info "  3. Copy the ops_... token"
    info "  4. export OP_SERVICE_ACCOUNT_TOKEN='ops_...'"
    exit 1
else
    pass "OP_SERVICE_ACCOUNT_TOKEN is set"
fi

# ── 3. Test authentication ────────────────────────────────────────────────────
echo ""
echo -e "${BOLD}[3/4] Testing 1Password authentication${RESET}"
if op vault list --format=json &>/dev/null; then
    pass "Authentication successful"
    if op vault get "${VAULT}" &>/dev/null; then
        pass "Vault '${VAULT}' is accessible"
    else
        fail "Vault '${VAULT}' not found or not accessible"
        echo ""
        info "Create the vault in 1Password UI, then grant the service account read access."
        exit 1
    fi
else
    fail "Authentication failed — check OP_SERVICE_ACCOUNT_TOKEN value"
    exit 1
fi

# ── 4. Check all required items and fields ───────────────────────────────────
echo ""
echo -e "${BOLD}[4/4] Checking vault items and fields${RESET}"

check_field() {
    local item="$1" field="$2"
    local ref="op://${VAULT}/${item}/${field}"
    if val=$(op read "${ref}" 2>/dev/null) && [[ -n "$val" ]]; then
        pass "${item}/${field}"
    else
        fail "${item}/${field}  ${YELLOW}(op read ${ref})${RESET}"
    fi
}

echo "  ${CYAN}── vCenter ──${RESET}"
check_field "vCenter" "server"
check_field "vCenter" "username"
check_field "vCenter" "password"
check_field "vCenter" "datacenter"
check_field "vCenter" "cluster"
check_field "vCenter" "datastore"
check_field "vCenter" "network"
check_field "vCenter" "build_folder"
check_field "vCenter" "template_folder"
check_field "vCenter" "build_test_folder"
check_field "vCenter" "deploy_prod_folder"
check_field "vCenter" "deploy_test_folder"

echo "  ${CYAN}── SSH-Admin ──${RESET}"
check_field "SSH-Admin" "username"
check_field "SSH-Admin" "password"
check_field "SSH-Admin" "pubkey"
check_field "SSH-Admin" "key_path"

echo "  ${CYAN}── Content-Library ──${RESET}"
check_field "Content-Library" "name"
check_field "Content-Library" "item_name"

echo "  ${CYAN}── Build-ISOs ──${RESET}"
check_field "Build-ISOs" "ubuntu_2404_iso_url"
check_field "Build-ISOs" "ubuntu_2404_iso_checksum"
check_field "Build-ISOs" "ubuntu_2604_iso_url"
check_field "Build-ISOs" "ubuntu_2604_iso_checksum"
check_field "Build-ISOs" "photon_iso_url"
check_field "Build-ISOs" "photon_iso_checksum"

echo "  ${CYAN}── Build-Config ──${RESET}"
check_field "Build-Config" "packer_firmware"
check_field "Build-Config" "template_cpu_count"
check_field "Build-Config" "template_memory_mb"
check_field "Build-Config" "template_disk_size_mb"

echo "  ${CYAN}── GitHub ──${RESET}"
check_field "GitHub" "github_pat"

# ── 5. Validate secrets.env resolves ─────────────────────────────────────────
echo ""
echo -e "${BOLD}[5/5] Validating secrets.env resolves via op run${RESET}"
if [[ -f "${SECRETS_ENV}" ]]; then
    if op run --env-file="${SECRETS_ENV}" -- env | grep -q "VCENTER_SERVER"; then
        pass "secrets.env resolves correctly"
        info "VCENTER_SERVER = $(op run --env-file="${SECRETS_ENV}" -- sh -c 'echo $VCENTER_SERVER')"
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
    echo -e "  ${BOLD}Run manage.py with:${RESET}"
    echo -e "  ${CYAN}export OP_SERVICE_ACCOUNT_TOKEN='ops_...'${RESET}"
    echo -e "  ${CYAN}python3 manage.py deploy ubuntu-2404-base 01${RESET}"
    echo ""
else
    echo -e "${RED}${BOLD}${ERRORS} check(s) failed. Fix the issues above before proceeding.${RESET}"
    echo ""
    echo -e "  Reference vault structure: ${CYAN}config/vault.yml.example${RESET}"
    exit 1
fi
