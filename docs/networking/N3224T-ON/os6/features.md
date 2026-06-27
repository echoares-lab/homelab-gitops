# OS6 Feature Notes

This file summarizes the features that matter for operating the Dell N3224T-ON in this homelab. It is not a full replacement for Dell's OS6 user guide.

## Hardware Capabilities

The N3224T-ON is a 1RU campus/access switch in the N3200-ON family.

Expected hardware profile:

| Capability | Notes |
| --- | --- |
| Access ports | 24 RJ45 `10/100/1000BASE-T` ports |
| Uplinks | 4 SFP+ `1/10GbE` ports |
| High-speed rear ports | 2 QSFP28 `100GbE` ports, commonly used for stacking on N-Series |
| Switching mode | Layer 2 and Layer 3 capable |
| Firmware layout | Dual OS6 images: active and backup |
| Management | In-band VLAN interface plus console; OS6 SSH is available |
| ONIE | Present on `-ON` models for network OS installation and recovery |

## OS6 Management Surface

Current local observations:

| Surface | Status |
| --- | --- |
| SSH CLI | Enabled and usable |
| SCP server | Disabled |
| SNMP | Available in OS6, but no communities were configured during inspection |
| RESTCONF/NETCONF/gNMI | Not observed on the running OS6 image |
| Ansible support | Supported through the `dellemc.os6` collection over `network_cli` |

OS6 is CLI-centered. For GitOps, prefer an Ansible workflow that renders intended config snippets and applies them through `dellemc.os6.os6_config`.

## Common Feature Areas

| Area | What to Manage |
| --- | --- |
| VLANs | Create VLAN IDs, names, access port assignment, trunk/general tagged membership. |
| Link aggregation | Configure LAG/port-channel interfaces for uplinks or server bonds. |
| Layer 3 | Static routes, VLAN interfaces, and routing features if the switch becomes a routed access layer. |
| Security | Local users, SSH, management ACLs, SNMPv3 if monitoring is required. |
| Monitoring | Interface counters, logs, LLDP neighbors, environmental state, SNMP traps if configured. |
| Firmware | Maintain active and backup images; keep OS6 on Dell's recommended N3200-ON version. |
| Recovery | Use ONIE only for NOS recovery or experiments with a clear rollback plan. |

## OS10 and SONiC Reality Check

Dell's official support matrix is the controlling source for production decisions:

| Model | OS6 | OS10 | Enterprise SONiC |
| --- | --- | --- | --- |
| `N3224T-ON` | Supported | Not supported | Not supported |

Community posts mention N-Series and SONiC experimentation, but no confirmed safe OS10 or SONiC path was found for this exact model. Keep OS10/SONiC research separated from operational management for this switch.

