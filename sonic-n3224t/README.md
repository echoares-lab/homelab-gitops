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

Known gaps: no `sonic_platform` API package for this board (pmon hardware daemons
inactive → no fan/thermal management; fans follow the controller's fallback behavior),
and the default `admin` credential should be rotated on any non-bench deployment.
