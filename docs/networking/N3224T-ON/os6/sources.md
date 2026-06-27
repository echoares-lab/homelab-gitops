# Sources

This file records source material used for the N3224T-ON OS6 documentation.

## Dell Sources

| Topic | Source |
| --- | --- |
| N3200-ON/E3200-ON OS support matrix | <https://www.dell.com/support/manuals/en-vc/networking-e3200-series/n3200-on_e3200-on_install_pub/introduction?guid=guid-88da49e2-d1fe-4f6d-b7b8-7b2c2a12d82a&lang=en-us> |
| Latest/recommended Dell networking code versions | <https://www.dell.com/support/kbdoc/en-us/000228560/minimum-recommended-and-latest-code-versions-for-networking-products> |
| N3200-ON OS6 `6.8.1.11` firmware package | <https://www.dell.com/support/home/en-us/drivers/driversdetails?driverid=ghxt5> |
| N2200/N3200 OS6 license installation | <https://www.dell.com/support/kbdoc/en-us/000126420/dell-emc-networking-n2200-n3200-os6-and-license-installation> |
| ONIE recovery live disk creation | <https://www.dell.com/support/kbdoc/en-id/000213926/creating-onie-recovery-livedisk> |
| N3200-ON installation guide PDF | <https://dl.dell.com/topicspdf/networking-n3200-on_install-guide3_en-us.pdf> |

## Automation Sources

| Topic | Source |
| --- | --- |
| Dell OS6 Ansible collection | <https://github.com/ansible-collections/dellemc.os6> |
| Ansible Dell OS6 platform guide | <https://docs.ansible.com/projects/ansible/latest/network/user_guide/platform_dellos6.html> |
| Dell OS6 Ansible collection docs | <https://docs.ansible.com/projects/ansible/latest/collections/dellemc/os6/index.html> |

## Community Sources

Community sources are useful for lab context but do not override Dell's support matrix.

| Topic | Source |
| --- | --- |
| ServeTheHome N2224X/N3200 discussion | <https://forums.servethehome.com/index.php?threads/dell-n2224x-on-power-switch-24x-2-5gbe-4x-sfp28-25gbe-2x-qsfp-257-99.48320/> |
| ServeTheHome power-consumption thread with N3224T-ON mentions | <https://forums.servethehome.com/index.php?threads/power-consumption-thread.34673/> |
| Reddit N3248/OS6/OS10/SONiC discussion | <https://www.reddit.com/r/networking/comments/v21mx7/dell_powerswitch_n3248pon_vs_powerswitch_s3048on/> |
| Level1Techs Dell OS10 guide for S5212F-ON | <https://forum.level1techs.com/t/dell-os10-switches-quick-start-configuration-guide-s5212f-on/178395> |
| Level1Techs SONiC setup discussion for S5212F-ON | <https://forum.level1techs.com/t/dell-s5212f-on-alternative-os-sonic-setup-guide-25gbe-100gbe-on-a-budget/198643> |

## Local Observations

Local facts came from read-only SSH commands run against `10.10.10.4` on 2026-06-20:

```text
show version
show system
show system id
show bootvar
show ip interface
show ip ssh
show snmp
```

Credentials are intentionally not documented here.

