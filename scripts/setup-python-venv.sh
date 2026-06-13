#!/usr/bin/env bash
# Pin CI venv to Python 3.12.
# Best match for Docker tests.

set -euo pipefail

VENV_DIR=".venv"
PYTHON_BIN="python3.12"

info()  { echo "[INFO]  $*"; }
ok()    { echo "[OK]    $*"; }
die()   { echo "[ERROR] $*" >&2; exit 1; }

# 1. Install python3.12-venv if missing
if ! dpkg -l | grep -q "python3.12-venv"; then
    info "Installing python3.12-venv..."
    sudo apt-get update -qq
    sudo apt-get install -y python3.12-venv
fi

# 2. Create venv using python3.12
info "Creating venv at $VENV_DIR using $PYTHON_BIN..."
$PYTHON_BIN -m venv "$VENV_DIR"
ok "Created venv"

# 3. Install dependencies
# shellcheck source=/dev/null
source "$VENV_DIR/bin/activate"
pip install --upgrade pip
pip install -r requirements.txt
ok "Dependencies installed in 3.12 venv"
