# Firmware and Recovery

This switch is already running Dell's current recommended OS6 release for the N3200-ON family: `6.8.1.11`.

## Current Firmware State

Observed with `show version` and `show bootvar`:

```text
Image File........................ N3200v6.8.1.11

unit active      backup      current-active next-active
---- ----------- ----------- -------------- --------------
1    6.8.1.11    6.7.1.10    6.8.1.11       6.8.1.11
```

Dell's current N3200-ON OS6 package is:

```text
N3200-ONv6.8.1.11.A15.zip
N3200v6.8.1.11.stk
```

Do not upgrade firmware unless Dell publishes a newer recommended N3200-ON OS6 release or a specific bug fix is needed.

## Pre-Change Checklist

Before firmware, ONIE, or NOS work:

1. Confirm physical console access.
2. Confirm the management port and console port are reachable.
3. Capture:

```text
show running-config
show startup-config
show version
show bootvar
show system id
show ip interface
```

4. Download and checksum the Dell OS6 image package.
5. Download the N3200-ON ONIE package or recovery media.
6. Confirm you can serve files by TFTP, FTP, SCP, HTTP, or USB as required by the chosen recovery path.
7. Keep a sanitized copy of the intended config in Git and a raw encrypted backup outside Git.

## OS6 Firmware Update Shape

Dell's driver page says to download the N3200-ON zip, extract the `.stk` image, and follow the included upgrade PDF. The exact commands should come from that release's PDF because Dell can change upgrade caveats by release.

High-level flow:

1. Copy the `.stk` image to the switch by a supported transfer method.
2. Install the image to the nonactive slot.
3. Set the next-active image.
4. Reload during a maintenance window.
5. Verify `show version`, `show bootvar`, management reachability, VLANs, and uplinks.
6. Save or adjust only after validation.

## ONIE Menu Options

The N3200-ON installation guide documents these ONIE options:

| Option | Effect |
| --- | --- |
| `ONIE: Install OS` | Starts NOS install and automatic discovery. |
| `ONIE: Rescue` | Boots to an ONIE prompt for manual install or repair. |
| `ONIE: Uninstall OS` | Deletes NOS partitions and configuration, except ONIE and diagnostics. |
| `ONIE: Update ONIE` | Updates ONIE. |
| `ONIE: Embed ONIE` | Formats disk and installs ONIE. |
| `ONIE: Diag ONIE` | Runs diagnostics. |

Use `ONIE: Rescue` first when possible. Use `ONIE: Uninstall OS` only when you intend to erase the installed NOS and configuration.

## Manual ONIE Install Pattern

From ONIE rescue mode:

```sh
onie-discovery-stop
ifconfig eth0 10.10.10.10 netmask 255.255.255.0 up
route add default gw 10.10.10.1
onie-nos-install ftp://10.10.10.50/path/to/onie-installer
```

Use an IP that does not conflict with any active host. Replace the FTP URL with the actual server and installer path.

## USB Install Pattern

ONIE can discover installers from USB when the USB drive is formatted with a supported filesystem such as FAT or EXT2 and the installer filename matches ONIE's expected installer naming rules, commonly starting with `onie-installer`.

Keep a labeled recovery USB with:

- Dell N3200-ON OS6 installer or recovery material.
- N3200-ON ONIE recovery media.
- A text file with this switch's management IP, gateway, and firmware version.

## If OS10 or SONiC Fails

Expected recovery path:

1. Connect serial console.
2. Boot to the ONIE menu.
3. Select `ONIE: Rescue`.
4. Stop discovery if needed with `onie-discovery-stop`.
5. Configure `eth0`.
6. Install a known-good supported NOS.

If partitions are corrupted:

1. Boot to ONIE.
2. Select `ONIE: Uninstall OS`.
3. Reinstall OS6 or another supported NOS.
4. Restore sanitized intended config through Ansible or manual CLI.

If ONIE is corrupted:

1. Create an ONIE recovery live USB from Dell's recovery instructions.
2. Boot the switch from USB.
3. Reinstall or embed ONIE.
4. Reinstall the NOS.

If BIOS or internal storage is damaged, recovery may require deeper hardware work and is outside normal firmware rollback.

## Risk Statement

Because Dell does not list OS10 or Enterprise SONiC support for `N3224T-ON`, any attempt to install them is an unsupported lab experiment. It can erase configuration, break boot, require ONIE recovery, or leave the switch without working ports if the platform definition is missing or wrong.

