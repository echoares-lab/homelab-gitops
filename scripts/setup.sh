#!/usr/bin/env bash
# Bootstrap all tooling dependencies for homelab-gitops.
# Run once on a fresh machine: bash scripts/setup.sh

set -euo pipefail

TOFU_VERSION="1.12.0"
VENV_DIR="venv."
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
die()   { echo "[ERROR] $*" >&2; exit 1; }

# ── 1. Python virtual environment ─────────────────────────────────────────────
info "Setting up Python venv at $REPO_ROOT/$VENV_DIR ..."
cd "$REPO_ROOT"

if [ ! -d "$VENV_DIR" ]; then
    python3 -m venv "$VENV_DIR"
    ok "Created venv"
else
    ok "venv already exists"
fi

# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"

pip install --quiet --upgrade pip
pip install --quiet -r requirements.txt
ok "Python dependencies installed"

# ── 2. OpenTofu ───────────────────────────────────────────────────────────────
if command -v tofu &>/dev/null; then
    INSTALLED=$(tofu version 2>/dev/null | head -1 | grep -oP '\d+\.\d+\.\d+' || true)
    ok "OpenTofu already installed: $INSTALLED"
else
    info "Installing OpenTofu v${TOFU_VERSION} ..."
    ARCH=$(dpkg --print-architecture)
    TMP=$(mktemp -d)
    curl -fsSL "https://github.com/opentofu/opentofu/releases/download/v${TOFU_VERSION}/tofu_${TOFU_VERSION}_${ARCH}.deb" \
        -o "$TMP/tofu.deb"
    sudo dpkg -i "$TMP/tofu.deb"
    rm -rf "$TMP"
    ok "OpenTofu v${TOFU_VERSION} installed"
fi

# ── 3. Packer ─────────────────────────────────────────────────────────────────
if command -v packer &>/dev/null; then
    ok "Packer already installed: $(packer version | head -1)"
else
    info "Installing Packer via HashiCorp apt repo ..."
    curl -fsSL https://apt.releases.hashicorp.com/gpg | sudo gpg --dearmor -o /usr/share/keyrings/hashicorp-archive-keyring.gpg
    echo "deb [signed-by=/usr/share/keyrings/hashicorp-archive-keyring.gpg] \
https://apt.releases.hashicorp.com $(lsb_release -cs) main" \
        | sudo tee /etc/apt/sources.list.d/hashicorp.list
    sudo apt-get update -qq
    sudo apt-get install -y packer
    ok "Packer installed"
fi

# ── 4. Ansible ────────────────────────────────────────────────────────────────
if command -v ansible &>/dev/null; then
    ok "Ansible already installed: $(ansible --version | head -1)"
else
    info "Installing Ansible ..."
    sudo apt-get update -qq
    sudo apt-get install -y ansible
    ok "Ansible installed"
fi

# ── 5. govc ───────────────────────────────────────────────────────────────────
if command -v govc &>/dev/null; then
    ok "govc already installed: $(govc version)"
else
    info "Installing latest govc to /usr/local/bin ..."
    GOVC_VERSION=$(curl -s https://api.github.com/repos/vmware/govmomi/releases/latest \
        | python3 -c "import sys,json; print(json.load(sys.stdin)['tag_name'])")
    curl -fsSL "https://github.com/vmware/govmomi/releases/download/${GOVC_VERSION}/govc_Linux_x86_64.tar.gz" \
        | tar -xz -C /tmp govc
    sudo mv /tmp/govc /usr/local/bin/govc
    ok "govc ${GOVC_VERSION} installed"
fi

# ── 6. Summary ────────────────────────────────────────────────────────────────
echo ""
echo "╔══════════════════════════════════════╗"
echo "║        Setup complete! Versions       ║"
echo "╠══════════════════════════════════════╣"
printf "║  %-36s ║\n" "Python:  $(python3 --version 2>&1)"
printf "║  %-36s ║\n" "Tofu:    $(tofu version 2>/dev/null | head -1)"
printf "║  %-36s ║\n" "Packer:  $(packer version 2>/dev/null | head -1)"
printf "║  %-36s ║\n" "Ansible: $(ansible --version 2>/dev/null | head -1)"
GOVC_BIN=$(command -v govc || echo "./build/govc")
printf "║  %-36s ║\n" "govc:    $($GOVC_BIN version 2>/dev/null || echo 'not found')"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Activate venv with:  source ${VENV_DIR}/bin/activate"
