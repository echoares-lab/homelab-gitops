# sonic-n3224t — community SONiC platform for the Dell N3224T-ON

Artifacts to run community SONiC (validated: `202411`, build `1201290`) on the Dell
PowerSwitch N3224T-ON (Helix5/BCM56372), which has no upstream SONiC platform — only the
48-port N3248TE sibling does. First brought up 2026-08-24 on `sw-core-01` hardware (bench).

- `apply-platform.sh <mgmt-ip>` — patches a freshly ONIE-installed **stock**
  `sonic-broadcom.bin` into the working 24x1G + 4x10G + 2x100G platform (idempotent;
  the header comment documents each step and why).
- `platform/` — golden copy of the resulting on-switch platform dir
  (`/usr/share/sonic/device/x86_64-dellemc_n3224t_c3338-r0`), captured after validation.

Fresh install: ONIE → `onie-nos-install http://<server>/sonic-broadcom.bin` → answer `y`
to the ASIC-type prompt → run `apply-platform.sh`. If the disk is occupied by OS6, run
`onie-boot-mode -o uninstall` + reboot first. Recovery to OS6: ONIE install the
`N3200-ONv6.8.1.x` ONIE installer from Dell's `Otherfiles/`.

Image identity: `sonic-broadcom.bin` sha256
`a506cbacdc03363eac59a8c8941fec496f96940298228865568d7121d6b5dd9f` (branch 202411,
Azure build 1201290). Mods do NOT survive `sonic-installer install` of a new image —
re-run `apply-platform.sh` after any image change.

## Status (2026-08-24, validated on bench hardware)

Working: ONIE install; platform/HWSKU detection; `syncd`/`swss` stable with the trimmed
30-port map (24x1G + 4x10G + 2x100G); VLAN/SVI config; mgmt over the OOB port; Dell board
support via the image's bundled `platform-modules-n3248te` deb (apply-platform.sh installs
it) — `dell_n3248te_platform` + `emc2305` fan controller + i2c muxes load, exposing 5x
tmp75 board sensors (27-40C observed) and PSU telemetry through hwmon.

Working — validated end-to-end 2026-08-24:
- **1G copper dataplane**: jack 1 linked at 1000FD (BCM54182 external PHY driver attached),
  bidirectional traffic proven (production ARP flood RX + iperf3 **944 Mbit/s** through the
  port). Root cause of the earlier failure: the N3224T is wired as "half an N3248TE"
  crosswise — jacks on SerDes lanes 1-24 but PHY MDIO at 0x20-0x39; the hybrid config.bcm
  in apply-platform.sh encodes this.
- Board sensors/fan controller drivers (see above), ONIE install, VLAN/SVI, mgmt via OOB.

Open items:
- SFP+ (`Ethernet48-51`) and 100G (`Ethernet52/56`) untested (no modules on the bench).
- Jacks 2-24 assumed by symmetry (same PHY blocks); only jack 1 traffic-tested.
- `pmon` SONiC-native fan/thermal integration still WIP; raw hwmon works.
- Default `admin` credential must be rotated for any non-bench use.
