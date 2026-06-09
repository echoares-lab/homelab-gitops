# op_connect_integration Ansible Role

Installs and configures integration with 1Password Connect server.

## Variables

- `op_connect_integration_server`: Connect server URL (default: https://10.10.10.30:8200)
- `op_connect_integration_token_path`: Path to API token file (default: /etc/op-connect/token)

## Usage

Include in playbook:

```yaml
- hosts: all
  roles:
    - op_connect_integration
```

Then use in tasks:

```yaml
- name: Get secret
  ansible.builtin.shell: |
    op run --server {{ op_connect_integration_server }} -- \
      op read op://homelab-gitops/prod/VCENTER_PASSWORD
  register: vcenter_password
  changed_when: false
  environment: "{{ op_connect_integration_env }}"
```

Or wrap entire playbook:

```bash
export OP_CONNECT_TOKEN=$(cat /etc/op-connect/token)
op run --server https://10.10.10.30:8200 -- \
  ansible-playbook -i localhost, \
  -e "ansible_connection=local" \
  ansible/site.yml
```

## Testing

```bash
ansible-playbook -i localhost, \
  -e "ansible_connection=local" \
  ansible/roles/op_connect_integration/tasks/main.yml
```
