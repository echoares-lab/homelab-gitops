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

# 2) port_config.ini: Ethernet0-23 on lanes 1-24 (physical jacks 1-24) + upstream
#    Ethernet48-51 (10G) and Ethernet52/56 (100G) rows
sudo cp "$HW/port_config.ini" "$HW/port_config.ini.orig48"
{ echo "# name        lanes    alias         index  speed   autoneg"
  for i in $(seq 0 23); do echo "Ethernet$i    $((i+1))    oneGigE1/$((i+1))    $((i+1))    1000    1"; done
  grep -E "^Ethernet(48|49|50|51|52|56)\b" "$HW/port_config.ini.orig48"
} | sudo tee "$HW/port_config.ini" >/dev/null

# 3) config.bcm — the validated HYBRID mapping. Empirically proven on hardware:
#    the N3224T is "half an N3248TE" wired crosswise — the 24 jacks ride SerDes
#    lanes 1-24 (ge0-23) but the three BCM54182 octal PHYs answer MDIO at the
#    UPPER-half addresses 0x20-0x39 (verified with `bcmcmd "phy dumpall c22"`).
#    So: keep the lower-half portmap, graft the upper-half PHY addressing onto it,
#    drop the upper-half port rows entirely (ASIC must create exactly the
#    configured ports or orchagent's removePortBulk SIGABRTs).
sudo python3 - <<PYEOF
import re
H="$HW"
src=open(H+"/hx5-n3248te-48x1G+4x10G.config.bcm").read().splitlines()
phyaddr={}; primoff={}
for l in src:
    m=re.match(r"port_phy_addr_(\d+)=(.*)",l)
    if m: phyaddr[int(m.group(1))]=m.group(2)
    m=re.match(r"phy_port_primary_and_offset_(\d+)=(.*)",l)
    if m: primoff[int(m.group(1))]=m.group(2)
out=[]
for l in src:
    m=re.match(r"(port_phy_addr|phy_port_primary_and_offset|portmap|dport_map_port|port_init_speed|port_init_autoneg)_(\d+)=",l)
    if m:
        n=int(m.group(2)); key=m.group(1)
        if 25<=n<=48: continue
        if key=="port_phy_addr" and 1<=n<=24:
            out.append("port_phy_addr_%d=%s"%(n,phyaddr[n+24])); continue
        if key=="phy_port_primary_and_offset" and 1<=n<=24:
            out.append("phy_port_primary_and_offset_%d=%s"%(n,primoff[n+24])); continue
    if l.startswith("port_gmii_mode_33="): continue
    out.append(l)
open(H+"/hx5-n3224t-24x1G+4x10G.config.bcm","w").write("\n".join(out)+"\n")
PYEOF
echo "SAI_INIT_CONFIG_FILE=/usr/share/sonic/hwsku/hx5-n3224t-24x1G+4x10G.config.bcm" \
  | sudo tee "$HW/sai.profile" >/dev/null

# 4) Dell board support: the image bundles the N3248TE platform-modules deb but never
#    installs it (platform-name mismatch). It loads dell_n3248te_platform + emc2305 (fan
#    controller) + i2c muxes and exposes 5x tmp75 board sensors + PSU telemetry on our
#    board too. Also stage the sonic_platform wheel where the service expects it.
DEB=$(ls /host/image-*/platform/x86_64-dellemc_n3248te_c3338-r0/platform-modules-n3248te_*.deb | head -1)
sudo dpkg -i --force-depends "$DEB"
W=/usr/share/sonic/device/x86_64-dellemc_n3248te_c3338-r0/sonic_platform-1.0-py3-none-any.whl
[ -f "$W" ] && sudo cp "$W" "$DST/"
sudo systemctl enable platform-modules-n3248te

# 5) factory config (brings the FEATURE table so pmon/lldp/snmp/gnmi enable)
sudo rm -f /etc/sonic/config_db.json
sudo config-setup factory
PORTS=$(sonic-cfggen -d --var-json PORT | python3 -c "import sys,json;print(len(json.load(sys.stdin)))")
[ "$PORTS" = "30" ] || { echo "FATAL: expected 30 ports, got $PORTS"; exit 1; }
sudo config save -y
echo "OK: platform applied, 30 ports, config saved. Rebooting..."
sudo reboot || true
REMOTE
echo "Done. Switch is rebooting; expect mgmt back via OOB DHCP in ~2-3 min."
