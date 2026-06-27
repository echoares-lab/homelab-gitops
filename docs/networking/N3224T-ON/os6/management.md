# OS6 Management and GitOps

The supported automation path for this switch is Ansible over SSH using Dell's OS6 collection. OpenTofu should not be used as the direct switch configuration engine for OS6.

## Recommended Inventory Variables

Use a host entry similar to this when adding the switch to Ansible inventory:

```yaml
dell_switch:
  ansible_host: 10.10.10.4
  ansible_user: matthew
  ansible_connection: ansible.netcommon.network_cli
  ansible_network_os: dellemc.os6.os6
  ansible_become: true
  ansible_become_method: enable
```

Do not commit plaintext switch passwords. Store credentials in Ansible Vault, OpenBao, 1Password, or the repository's existing secret-management path.

## Required Collections

Install the Dell OS6 collection explicitly:

```bash
ansible-galaxy collection install dellemc.os6
```

Useful modules:

| Module | Use |
| --- | --- |
| `dellemc.os6.os6_command` | Read-only command collection. |
| `dellemc.os6.os6_config` | Apply configuration lines and snippets. |
| `dellemc.os6.os6_facts` | Gather OS6 device facts where supported. |

## GitOps Model

Use Git as the source of truth for intended state, not for raw switch dumps.

Recommended model:

1. Collect facts and sanitized current config.
2. Define intended VLANs, descriptions, trunks, LAGs, and management settings in YAML.
3. Render OS6 config snippets from templates.
4. Apply with `os6_config`.
5. Save only after validation.
6. Capture post-change facts and diff output.

## Minimal Read-Only Playbook

```yaml
---
- name: Collect Dell OS6 switch state
  hosts: dell_switch
  gather_facts: false

  tasks:
    - name: Collect version and boot state
      dellemc.os6.os6_command:
        commands:
          - show version
          - show bootvar
          - show ip interface
          - show ip ssh
      register: os6_state

    - name: Print command output
      ansible.builtin.debug:
        var: os6_state.stdout_lines
```

## Minimal Config Pattern

Use `parents` for scoped interface changes and keep the snippet small:

```yaml
---
- name: Configure a Dell OS6 interface description
  hosts: dell_switch
  gather_facts: false

  tasks:
    - name: Set interface description
      dellemc.os6.os6_config:
        parents:
          - interface Gi1/0/1
        lines:
          - description proxmox-node-01
```

Validate syntax on a noncritical port before automating larger config sections.

## Backup Workflow

Before any config change:

```yaml
---
- name: Backup Dell OS6 config
  hosts: dell_switch
  gather_facts: false

  tasks:
    - name: Capture running config
      dellemc.os6.os6_command:
        commands:
          - show running-config
      register: running_config

    - name: Save local raw backup outside committed desired-state paths
      ansible.builtin.copy:
        content: "{{ running_config.stdout[0] }}"
        dest: "artifacts/network/dell-switch-running-config.txt"
        mode: "0600"
      delegate_to: localhost
```

Do not commit `artifacts/network/dell-switch-running-config.txt` unless it has been reviewed and sanitized.

## OpenTofu Position

OpenTofu is useful for infrastructure resources that have stable providers. No Dell OS6 switch provider was identified. Keep OS6 switch config in Ansible and use OpenTofu only for surrounding infrastructure such as VMs, DNS, or services that already have providers in this repository.

## MCP Position

No direct MCP server for Dell OS6 or N3224T-ON was identified. Practical MCP options are indirect:

- NetBox or Nautobot as the network source of truth, exposed through an MCP server.
- A custom MCP server that wraps approved read-only Ansible playbooks.
- A custom MCP server that wraps restricted SSH commands, with a deny-by-default command allowlist.

For this switch, prefer read-only MCP operations until Ansible desired state and rollback are mature.

