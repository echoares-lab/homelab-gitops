# OS6 Command Reference

Commands in this file are intended for read-only discovery and cautious OS6 administration. Use `enable` for privileged show commands when needed.

## Session Basics

```text
enable
show version
show system
show system id
show bootvar
show ip interface
show ip ssh
show snmp
```

Notes:

- OS6 on this switch rejected `terminal length 0` during the initial inspection. Expect paged output and press space or `q` as needed.
- Some IOS-like commands and pipe filters are not supported on this OS6 image.

## Identity and Inventory

```text
show version
show system
show system id
show bootvar
```

Use these before and after any firmware or recovery work. Capture the output in the change record.

## Management IP

```text
show ip interface
```

The observed management state was:

```text
Default Gateway................................ 10.10.10.1
Vl1 Up 10.10.10.4 255.255.255.0 Manual
```

## SSH

```text
show ip ssh
```

Observed state:

```text
SSH Server enabled.  Port: 22
Protocol Level: Version 2.
SCP server Administrative Mode: Disabled
```

If automation later needs SCP, enable it intentionally and document why.

## SNMP

```text
show snmp
```

No community strings were configured when inspected. If monitoring is added, prefer SNMPv3 over community-based SNMP where OS6 supports the required collector behavior.

## Interfaces

```text
show interfaces status
show interfaces switchport
show interfaces counters
show interfaces description
show lldp neighbors
show lldp neighbors detail
```

Use these to map physical ports before GitOps automation claims ownership of VLANs or descriptions.

## VLANs

```text
show vlan
show vlan brief
show interfaces switchport
show running-config
```

Use full `show running-config` only when you are prepared to handle secrets safely. Store sanitized copies in Git, not raw device exports.

## LAGs and Uplinks

```text
show interfaces port-channel
show interfaces port-channel brief
show lacp
show lacp interfaces
```

Command support can vary by OS6 version and feature state. If one command fails, use context help:

```text
show ?
show interfaces ?
```

## Environment and Health

```text
show system
show logging
show process cpu
show memory
```

`show system` includes temperature, fan, and power supply state. Capture it before planned maintenance.

## Config Backup

Preferred manual backup flow:

```text
show running-config
show startup-config
```

Recommended handling:

- Save raw output outside Git if it includes credentials, keys, SNMP strings, or other secrets.
- Commit only sanitized desired state or sanitized backup excerpts.
- Record `show version` and `show bootvar` next to the backup so the config is tied to a firmware version.

## Config Save

After intentional changes:

```text
copy running-config startup-config
```

Avoid saving exploratory or partial config changes.

