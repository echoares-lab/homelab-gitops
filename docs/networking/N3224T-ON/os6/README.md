# Dell N3224T-ON OS6 Documentation

This folder documents the Dell PowerSwitch N3224T-ON currently managed in the homelab and the practical OS6 workflows for operating it safely.

## Local Switch Facts

Observed over SSH on 2026-06-20:

| Field | Value |
| --- | --- |
| Management IP | `10.10.10.4` |
| Hostname | `dell-switch` |
| Model | `N3224T-ON` |
| Platform family | Dell PowerSwitch N3200-ON |
| Running image | `N3200v6.8.1.11` |
| Active OS6 version | `6.8.1.11` |
| Backup OS6 version | `6.7.1.10` |
| Management VLAN interface | `Vl1` |
| Management default gateway | `10.10.10.1` |
| SSH | Enabled on TCP/22 |
| SCP server | Disabled |
| SNMP communities | None configured at time of check |

## Support Position

Dell's N3200-ON/E3200-ON installation guide lists the `N3224T-ON` as supported for OS6 and not supported for OS10 or Dell Enterprise SONiC. Treat OS6 as the supported operating system for this exact switch.

The installed OS6 version, `6.8.1.11`, is Dell's latest and recommended code for `N3200-ON with OS6.8` as of Dell's code-version article last updated 2026-06-15.

## File Map

| File | Purpose |
| --- | --- |
| [features.md](features.md) | Feature overview for N3224T-ON on OS6. |
| [commands.md](commands.md) | Practical CLI command reference. |
| [management.md](management.md) | GitOps, Ansible, backup, and credential handling guidance. |
| [firmware-and-recovery.md](firmware-and-recovery.md) | OS6 firmware workflow, ONIE recovery, and OS10/SONiC risk notes. |
| [sources.md](sources.md) | Source links and notes used to build this documentation. |

## Operating Rule

Use OS6-native management unless a lab experiment explicitly requires ONIE. Do not try OS10 or SONiC on this switch without serial console access, a maintenance window, and a tested path back to OS6.

