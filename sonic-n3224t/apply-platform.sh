#!/usr/bin/env bash
# apply-platform.sh — turn a STOCK community sonic-broadcom.bin install on a Dell
# N3224T-ON into the working 24x1G+4x10G+2x100G platform, over SSH.
#
# The stock community image has no platform for the N3224T-ON (only the 48-port
# N3248TE is upstream). This script re-applies the validated adaptation:
#   1. clone the upstream N3248TE platform dir as x86_64-dellemc_n3224t_c3338-r0
#      (name MUST match `onie-sysinfo -p` on this box)
#   2. HWSKU DellEMC-N3224T: trim port_config.ini to Ethernet0-23 + 48-51 + 52/56
#   3. trim config.bcm: drop per-port keys for phantom logical ports 25-48
#      (ASIC must create exactly the configured ports; otherwise orchagent's
#      removePortBulk hits SAI_STATUS_FAILURE and SIGABRTs — learned the hard way)
#   4. regenerate factory config (FEATURE table included) and save
#
# Usage: ./apply-platform.sh <switch-mgmt-ip> [ssh-user]
#   After a fresh ONIE install, find the DHCP address ONIE/SONiC took on the
#   OOB mgmt port (Technitium leases), default login admin/YourPaSsWoRd.
#
# Idempotent: safe to re-run. Requires: sshpass or an SSH key already set up.
set -euo pipefail

IP="${1:?usage: apply-platform.sh <switch-mgmt-ip> [user]}"
USER="${2:-admin}"
SSH_OPTS=(-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10)

ssh "${SSH_OPTS[@]}" "${USER}@${IP}" 'bash -s' <<'REMOTE'
set -euo pipefail
D=/usr/share/sonic/device
SRC=$D/x86_64-dellemc_n3248te_c3338-r0
DST=$D/x86_64-dellemc_n3224t_c3338-r0
HW=$DST/DellEMC-N3224T

# sanity: right box?
grep -q "n3224t" /host/machine.conf || { echo "FATAL: not an N3224T (machine.conf)"; exit 1; }
[ -d "$SRC" ] || { echo "FATAL: upstream N3248TE platform missing from image"; exit 1; }

# 1) platform dir (fresh each run; firstboot may have pre-created an empty one)
sudo rm -rf "$DST"
sudo cp -r "$SRC" "$DST"
sudo mv "$DST/DellEMC-N3248TE" "$HW"
echo "DellEMC-N3224T t1" | sudo tee "$DST/default_sku" >/dev/null
sudo sed -i "s/DellEMC-N3248TE/DellEMC-N3224T/g" "$DST/platform.json"

# 2) port_config.ini: keep header + Ethernet0-23 (lanes 1-24) + Ethernet48-51 (10G)
#    + Ethernet52/56 (100G); drop phantom copper Ethernet24-47
sudo awk '/^#/ {print; next}
     $1 !~ /^Ethernet/ {print; next}
     { n=$1; sub(/^Ethernet/,"",n); n=n+0; if (n<=23 || n>=48) print }' \
     "$HW/port_config.ini" | sudo tee "$HW/port_config.ini.new" >/dev/null
sudo mv "$HW/port_config.ini.new" "$HW/port_config.ini"

# 3) config.bcm: ASIC must create exactly these ports
sudo cp "$HW/hx5-n3248te-48x1G+4x10G.config.bcm" "$HW/hx5-n3224t-24x1G+4x10G.config.bcm"
for n in $(seq 25 48); do
  sudo sed -i "/^portmap_${n}=/d; /^phy_port_primary_and_offset_${n}=/d; \
               /^port_phy_addr_${n}=/d; /^dport_map_port_${n}=/d; \
               /^port_init_speed_${n}=/d; /^port_init_autoneg_${n}=/d" \
      "$HW/hx5-n3224t-24x1G+4x10G.config.bcm"
done
sudo sed -i "/^port_gmii_mode_33=/d" "$HW/hx5-n3224t-24x1G+4x10G.config.bcm"
echo "SAI_INIT_CONFIG_FILE=/usr/share/sonic/hwsku/hx5-n3224t-24x1G+4x10G.config.bcm" \
  | sudo tee "$HW/sai.profile" >/dev/null

# 4) factory config (brings the FEATURE table so pmon/lldp/snmp/gnmi enable)
sudo rm -f /etc/sonic/config_db.json
sudo config-setup factory
PORTS=$(sonic-cfggen -d --var-json PORT | python3 -c "import sys,json;print(len(json.load(sys.stdin)))")
[ "$PORTS" = "30" ] || { echo "FATAL: expected 30 ports, got $PORTS"; exit 1; }
sudo config save -y
echo "OK: platform applied, 30 ports, config saved. Rebooting..."
sudo reboot || true
REMOTE
echo "Done. Switch is rebooting; expect mgmt back via OOB DHCP in ~2-3 min."
