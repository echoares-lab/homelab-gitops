#!/usr/bin/env bash
set -e

# Install or update immutable OS binaries
# Downloads binaries to /usr/local/bin or ~/.local/bin depending on permissions

DEST_DIR="/usr/local/bin"
if [ ! -w "$DEST_DIR" ]; then
    DEST_DIR="$HOME/.local/bin"
    mkdir -p "$DEST_DIR"
    echo "Warning: /usr/local/bin is not writable. Installing to $DEST_DIR"
    echo "Make sure $DEST_DIR is in your PATH."
fi

echo "Installing/Updating talosctl..."
curl -sL https://github.com/siderolabs/talos/releases/latest/download/talosctl-linux-amd64 -o "$DEST_DIR/talosctl"
chmod +x "$DEST_DIR/talosctl"

echo "Installing/Updating butane (for Fedora CoreOS and Flatcar)..."
curl -sL https://github.com/coreos/butane/releases/latest/download/butane-x86_64-unknown-linux-gnu -o "$DEST_DIR/butane"
chmod +x "$DEST_DIR/butane"

echo "Installing/Updating ct (Config Transpiler for legacy Flatcar)..."
# Get latest version of ct
CT_LATEST=$(curl -s https://api.github.com/repos/flatcar/container-linux-config-transpiler/releases/latest | grep '"tag_name":' | sed -E 's/.*"([^"]+)".*/\1/')
curl -sL "https://github.com/flatcar/container-linux-config-transpiler/releases/download/${CT_LATEST}/ct-${CT_LATEST}-x86_64-unknown-linux-gnu" -o "$DEST_DIR/ct"
chmod +x "$DEST_DIR/ct"

echo "Successfully installed immutable OS tools to $DEST_DIR:"
"$DEST_DIR/talosctl" version --client | head -n 1
"$DEST_DIR/butane" --version
"$DEST_DIR/ct" -version
