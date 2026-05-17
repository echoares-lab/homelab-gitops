#!/usr/bin/env bash
# scripts/op-vault-setup.sh
# Installs 1Password CLI, prompts for all secrets, and uploads them to the Homelab-GitOps vault.
#
# Usage:
#   bash scripts/op-vault-setup.sh
#
# Requires sudo for CLI install. You'll be prompted for an ops_... service account token.

set -euo pipefail

VAULT="Homelab-GitOps"

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
BOLD='\033[1m'
DIM='\033[2m'
RESET='\033[0m'

ok()     { echo -e "  ${GREEN}✓${RESET} $1"; }
err()    { echo -e "  ${RED}✗${RESET} $1"; }
info()   { echo -e "  ${CYAN}→${RESET} $1"; }
warn()   { echo -e "  ${YELLOW}!${RESET} $1"; }
section(){ echo -e "\n${BOLD}$1${RESET}"; }

# Prompt for a plain-text value. Usage: prompt_text "Label" varname ["default"]
prompt_text() {
    local label="$1" varname="$2" default="${3:-}"
    local hint=""
    [[ -n "$default" ]] && hint=" ${DIM}[${default}]${RESET}"
    local val
    read -rp "$(echo -e "    ${label}${hint}: ")" val
    [[ -z "$val" && -n "$default" ]] && val="$default"
    printf -v "$varname" '%s' "$val"
}

# Prompt hidden (password/token). Usage: prompt_secret "Label" varname
prompt_secret() {
    local label="$1" varname="$2"
    local val
    read -rsp "$(echo -e "    ${label} ${DIM}(hidden)${RESET}: ")" val
    echo ""
    printf -v "$varname" '%s' "$val"
}

# Prompt y/n. Usage: confirm "Question" && do_thing
confirm() {
    local yn
    read -rp "$(echo -e "    ${YELLOW}?${RESET} $1 [y/N] ")" yn
    [[ "$yn" =~ ^[Yy]$ ]]
}

# Create or update a vault item. Usage: upsert_item "Title" "Category" field1 field2 ...
upsert_item() {
    local title="$1" category="$2"
    shift 2

    if op item get "$title" --vault "$VAULT" &>/dev/null; then
        op item edit "$title" --vault "$VAULT" "$@" --format json >/dev/null
        ok "Updated:  ${BOLD}${title}${RESET}"
    else
        op item create --category "$category" --title "$title" --vault "$VAULT" "$@" --format json >/dev/null
        ok "Created:  ${BOLD}${title}${RESET}"
    fi
}

# ── 1. Install op CLI ──────────────────────────────────────────────────────────
install_op_cli() {
    section "[1/6] 1Password CLI"

    if command -v op &>/dev/null; then
        ok "Already installed — $(op --version)"
        return
    fi

    info "Installing via apt..."

    if ! command -v apt-get &>/dev/null; then
        err "Cannot auto-install: apt-get not found."
        echo -e "  Install manually: ${CYAN}https://developer.1password.com/docs/cli/get-started/${RESET}"
        exit 1
    fi

    # Add APT signing key
    curl -sS https://downloads.1password.com/linux/keys/1password.asc \
        | sudo gpg --dearmor --yes -o /usr/share/keyrings/1password-archive-keyring.gpg

    # Add APT repository
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/1password-archive-keyring.gpg] https://downloads.1password.com/linux/debian/$(dpkg --print-architecture) stable main" \
        | sudo tee /etc/apt/sources.list.d/1password.list >/dev/null

    # Add debsig policy
    sudo mkdir -p /etc/debsig/policies/AC2D62742012EA22/
    curl -sS https://downloads.1password.com/linux/debian/debsig/1password.pol \
        | sudo tee /etc/debsig/policies/AC2D62742012EA22/1password.pol >/dev/null

    sudo mkdir -p /usr/share/debsig/keyrings/AC2D62742012EA22
    curl -sS https://downloads.1password.com/linux/keys/1password.asc \
        | sudo gpg --dearmor --yes -o /usr/share/debsig/keyrings/AC2D62742012EA22/debsig.gpg

    sudo apt update
    sudo apt install -y 1password-cli
    ok "Installed — $(op --version)"
}

# ── 2. Auth ────────────────────────────────────────────────────────────────────
setup_auth() {
    section "[2/6] Authentication"

    if [[ -z "${OP_SERVICE_ACCOUNT_TOKEN:-}" ]]; then
        echo ""
        echo -e "  ${YELLOW}You need a Service Account token (ops_...).${RESET}"
        echo -e "  ${DIM}1Password → Settings → Developer → Service Accounts${RESET}"
        echo -e "  ${DIM}Scope: read + write on '${VAULT}' vault (create it first if needed).${RESET}"
        echo ""
        prompt_secret "OP_SERVICE_ACCOUNT_TOKEN" OP_SERVICE_ACCOUNT_TOKEN
        export OP_SERVICE_ACCOUNT_TOKEN
        echo ""
        info "Token saved for this session. To persist it:"
        echo -e "      ${DIM}export OP_SERVICE_ACCOUNT_TOKEN='${OP_SERVICE_ACCOUNT_TOKEN:0:12}...'${RESET}"
    else
        ok "OP_SERVICE_ACCOUNT_TOKEN already set"
    fi

    if ! op vault list --format json &>/dev/null; then
        err "Authentication failed — check your token and try again"
        exit 1
    fi
    ok "Authenticated"
}

# ── 3. Ensure vault exists ─────────────────────────────────────────────────────
ensure_vault() {
    section "[3/6] Vault"

    if op vault get "$VAULT" &>/dev/null; then
        ok "Vault '${VAULT}' exists"
    else
        info "Vault '${VAULT}' not found."
        if confirm "Create it now?"; then
            op vault create "$VAULT" --format json >/dev/null
            ok "Vault '${VAULT}' created"
        else
            err "Vault required — exiting."
            exit 1
        fi
    fi
}

# ── 4. Collect secrets ─────────────────────────────────────────────────────────
collect_all() {
    section "[4/6] Collect & upload secrets"
    echo -e "  ${DIM}Press Enter to accept defaults shown in [brackets].${RESET}"

    # ── vCenter ────────────────────────────────────────────────────────────────
    echo -e "\n  ${BOLD}${CYAN}── vCenter ──${RESET}"
    prompt_text    "Hostname or IP (e.g. vcenter.local)"             VC_SERVER
    prompt_text    "Username (e.g. administrator@vsphere.local)"     VC_USER
    prompt_secret  "Password"                                         VC_PASS
    prompt_text    "Datacenter name"                                  VC_DC
    prompt_text    "Cluster name"                                     VC_CLUSTER
    prompt_text    "Datastore name"                                   VC_DS
    prompt_text    "Network / portgroup name"                         VC_NET
    prompt_text    "Build folder path"        VC_BUILD_FOLDER         "Templates/Build"
    prompt_text    "Template folder path"     VC_TMPL_FOLDER          "Templates/Golden"
    prompt_text    "Build-test folder path"   VC_BUILD_TEST_FOLDER    "Templates/Build-Test"
    prompt_text    "Deploy prod folder path"  VC_PROD_FOLDER          "Workloads/Prod"
    prompt_text    "Deploy test folder path"  VC_TEST_FOLDER          "Workloads/Test"

    upsert_item "vCenter" "Login" \
        "server[text]=${VC_SERVER}" \
        "username[text]=${VC_USER}" \
        "password[password]=${VC_PASS}" \
        "datacenter[text]=${VC_DC}" \
        "cluster[text]=${VC_CLUSTER}" \
        "datastore[text]=${VC_DS}" \
        "network[text]=${VC_NET}" \
        "build_folder[text]=${VC_BUILD_FOLDER}" \
        "template_folder[text]=${VC_TMPL_FOLDER}" \
        "build_test_folder[text]=${VC_BUILD_TEST_FOLDER}" \
        "deploy_prod_folder[text]=${VC_PROD_FOLDER}" \
        "deploy_test_folder[text]=${VC_TEST_FOLDER}"

    # ── SSH-Admin ──────────────────────────────────────────────────────────────
    echo -e "\n  ${BOLD}${CYAN}── SSH-Admin ──${RESET}"
    prompt_text    "SSH admin username"       SSH_USER     "ansible"
    prompt_secret  "SSH admin password (blank = key-only)"  SSH_PASS
    prompt_text    "SSH private key path"     SSH_KEY_PATH "~/.ssh/id_ed25519"

    local expanded_key="${SSH_KEY_PATH/#\~/$HOME}"
    local pubkey_file="${expanded_key}.pub"
    local SSH_PUBKEY=""

    if [[ -f "$pubkey_file" ]]; then
        SSH_PUBKEY=$(cat "$pubkey_file")
        info "Read public key from ${pubkey_file}"
    else
        warn "No .pub file at ${pubkey_file}"
        prompt_text "Public key file path (or leave blank to skip)" PUBKEY_PATH ""
        if [[ -n "$PUBKEY_PATH" && -f "$PUBKEY_PATH" ]]; then
            SSH_PUBKEY=$(cat "$PUBKEY_PATH")
        else
            warn "Skipping pubkey — edit the SSH-Admin item later to add it"
        fi
    fi

    upsert_item "SSH-Admin" "Login" \
        "username[text]=${SSH_USER}" \
        "password[password]=${SSH_PASS}" \
        "pubkey[text]=${SSH_PUBKEY}" \
        "key_path[text]=${SSH_KEY_PATH}"

    # ── Content-Library ────────────────────────────────────────────────────────
    echo -e "\n  ${BOLD}${CYAN}── Content-Library ──${RESET}"
    prompt_text "vSphere content library name"            CL_NAME     "Homelab"
    prompt_text "Template item name inside the library"   CL_ITEM     "ubuntu-2404-base"

    upsert_item "Content-Library" "Secure Note" \
        "name[text]=${CL_NAME}" \
        "item_name[text]=${CL_ITEM}"

    # ── Build-ISOs ─────────────────────────────────────────────────────────────
    echo -e "\n  ${BOLD}${CYAN}── Build-ISOs ──${RESET}"
    info "Leave blank for fields you don't need yet — you can update them later"

    prompt_text "Ubuntu 24.04 ISO URL"        U2404_URL  "https://releases.ubuntu.com/24.04/ubuntu-24.04.2-live-server-amd64.iso"
    prompt_text "Ubuntu 24.04 ISO checksum"   U2404_SUM  ""
    prompt_text "Ubuntu 26.04 ISO URL"        U2604_URL  ""
    prompt_text "Ubuntu 26.04 ISO checksum"   U2604_SUM  ""
    prompt_text "Photon OS ISO URL"           PHOTON_URL ""
    prompt_text "Photon OS ISO checksum"      PHOTON_SUM ""

    upsert_item "Build-ISOs" "Secure Note" \
        "ubuntu_2404_iso_url[text]=${U2404_URL}" \
        "ubuntu_2404_iso_checksum[text]=${U2404_SUM}" \
        "ubuntu_2604_iso_url[text]=${U2604_URL}" \
        "ubuntu_2604_iso_checksum[text]=${U2604_SUM}" \
        "photon_iso_url[text]=${PHOTON_URL}" \
        "photon_iso_checksum[text]=${PHOTON_SUM}"

    # ── Build-Config ───────────────────────────────────────────────────────────
    echo -e "\n  ${BOLD}${CYAN}── Build-Config ──${RESET}"
    prompt_text "Packer firmware"       PKR_FIRMWARE   "efi"
    prompt_text "Template CPU count"    TMPL_CPU       "2"
    prompt_text "Template memory (MB)"  TMPL_MEM       "4096"
    prompt_text "Template disk (MB)"    TMPL_DISK      "32768"

    upsert_item "Build-Config" "Secure Note" \
        "packer_firmware[text]=${PKR_FIRMWARE}" \
        "template_cpu_count[text]=${TMPL_CPU}" \
        "template_memory_mb[text]=${TMPL_MEM}" \
        "template_disk_size_mb[text]=${TMPL_DISK}"

    # ── GitHub ─────────────────────────────────────────────────────────────────
    echo -e "\n  ${BOLD}${CYAN}── GitHub ──${RESET}"
    info "PAT needs scopes: repo, workflow, admin:org (for runner registration)"
    info "Create at: github.com → Settings → Developer settings → Personal access tokens"
    prompt_secret "GitHub Personal Access Token (ghp_...)" GH_PAT

    upsert_item "GitHub" "Login" \
        "github_pat[password]=${GH_PAT}"
}

# ── 5. Validate ────────────────────────────────────────────────────────────────
run_validation() {
    section "[5/6] Validation"

    local setup_script
    setup_script="$(cd "$(dirname "$0")" && pwd)/op-setup.sh"

    if [[ -f "$setup_script" ]]; then
        bash "$setup_script"
    else
        warn "scripts/op-setup.sh not found — run it manually to verify"
    fi
}

# ── 6. Next steps ──────────────────────────────────────────────────────────────
print_next_steps() {
    section "[6/6] Remaining manual steps"
    echo ""
    echo -e "  ${BOLD}Step 1 — Add GitHub Actions secret${RESET}"
    echo -e "  ${DIM}Repo → Settings → Secrets and variables → Actions → New repository secret${RESET}"
    echo -e "  ${DIM}Name:  OP_SERVICE_ACCOUNT_TOKEN${RESET}"
    echo -e "  ${DIM}Value: your ops_... token${RESET}"
    echo ""
    echo -e "  ${BOLD}Step 2 — Test the auto-wrap (token must be exported in your shell)${RESET}"
    echo -e "  ${CYAN}  export OP_SERVICE_ACCOUNT_TOKEN='ops_...'${RESET}"
    echo -e "  ${CYAN}  python3 manage.py lint ubuntu-2404-base 01${RESET}"
    echo ""
    echo -e "  ${BOLD}Step 3 — Remove old vault files once confirmed working${RESET}"
    echo -e "  ${CYAN}  rm config/vault.yml config/.vault_pass${RESET}"
    echo ""
    echo -e "  ${BOLD}Step 4 — Push the branch and confirm smoke-test CI passes${RESET}"
    echo -e "  ${DIM}The workflow will install op CLI and validate secrets.env resolves${RESET}"
    echo ""
}

# ── Main ───────────────────────────────────────────────────────────────────────
main() {
    echo ""
    echo -e "${BOLD}╔══════════════════════════════════════════╗${RESET}"
    echo -e "${BOLD}║   1Password Vault Setup                  ║${RESET}"
    echo -e "${BOLD}║   homelab-gitops / Homelab-GitOps        ║${RESET}"
    echo -e "${BOLD}╚══════════════════════════════════════════╝${RESET}"

    install_op_cli
    setup_auth
    ensure_vault
    collect_all
    run_validation
    print_next_steps
}

main "$@"
