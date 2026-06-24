# Ansible Role and Playbook Ownership

This document defines ownership categories for Ansible content so host
configuration remains understandable as roles and playbooks grow. It documents
the current layout only; it does not require role rewrites.

## Ownership Categories

| Category | Owns | Use when |
| --- | --- | --- |
| Base | Common host state that should be safe across broad OS/profile groups. | The role configures baseline packages, host identity, SSH posture, or profile-level hygiene. |
| Platform | Shared infrastructure substrate used by multiple workloads. | The role installs observability, container, Kubernetes, secrets, or other reusable platform services. |
| Workloads | A concrete application, development workstation, or service endpoint. | The role expresses what a specific host is for. |
| Runner | GitHub Actions runner hosts and their CI toolchain. | The role creates, registers, maintains, or synchronizes self-hosted runner capacity. |
| Networking | DNS, DHCP, firewall-adjacent, or network appliance configuration. | The role owns network control-plane behavior or network appliance deployment. |
| Legacy | Historical scaffolding or compatibility content that is not part of the preferred path. | The role remains in the tree but new automation should avoid extending it without an explicit migration decision. |

## Role Map

| Role | Category | Current responsibility |
| --- | --- | --- |
| `base` | Base | Sets hostnames, updates packages, removes insecure packages, and installs common utilities. |
| `security` | Base | Applies SSH hardening and baseline Ubuntu firewall posture. |
| `log_retention` | Base | Applies profile-owned logrotate and journald retention policy. |
| `alloy` | Platform | Installs and configures Grafana Alloy monitoring agents. |
| `docker` | Platform | Installs and starts Docker on Ubuntu or Photon hosts. |
| `docker_metrics` | Platform | Adds Docker TLS and metrics configuration after Docker is present. |
| `k3s_server` | Platform | Installs and initializes a single-server k3s control plane. |
| `op_connect_integration` | Platform | Configures 1Password Connect access for hosts that still need that integration path. |
| `dev_cloudflare` | Workloads | Builds the Cloudflare Access automation development workstation toolchain. |
| `dev_combined` | Workloads | Builds a combined homelab and Cloudflare development workstation. |
| `dev_homelab` | Workloads | Builds the homelab-gitops development workstation toolchain. |
| `mcp_gateway` | Workloads | Deploys the MCP Gateway container stack. |
| `github_runner_base` | Runner | Prepares runner host packages, storage, Node, browser, and shared CI prerequisites. |
| `github_runner` | Runner | Creates the runner user, installs the GitHub Actions runner, and registers it. |
| `github_runner_ci` | Runner | Applies aggregated repository CI requirements to runner hosts. |
| `dns_technitium` | Networking | Installs and configures Technitium DNS on Photon OS hosts. |
| `engenius_epc` | Networking | Deploys the EnGenius Private Cloud network appliance stack. |
| `q` | Legacy | Empty scaffold role retained for historical compatibility. |
| `technitium` | Legacy | Empty older Technitium role retained after `dns_technitium` became the active DNS role. |

## Playbook Map

| Playbook | Owner | Current scope |
| --- | --- | --- |
| `ansible/site.yml` | Base / Platform / Workloads / Networking | Main dynamic inventory entrypoint. Applies common roles to broad tag groups and workload roles to specific tags. |
| `ansible/apply_dns.yml` | Networking | Focused DNS host configuration using `base`, `security`, and `dns_technitium`. |
| `ansible/cloudflare-dev.yml` | Workloads | Builds Cloudflare development workstations with a shared runner-style baseline. |
| `ansible/combined-dev.yml` | Workloads | Builds combined development workstations. |
| `ansible/homelab-dev.yml` | Workloads | Builds homelab-gitops development workstations. |
| `ansible/cloudflare-runner.yml` | Runner | Builds and registers Cloudflare Access organization runners. |
| `ansible/git-test-runner.yml` | Runner | Builds and registers test/CI runners. |
| `ansible/runner-maintenance.yml` | Runner | Repairs existing runner host baseline without re-registration. |
| `ansible/sync-github-ci-runners.yml` | Runner | Applies aggregated CI runner requirements to existing runners. |
| `ansible/deploy.yml` | Platform | Provisions a VM from the golden template through vCenter modules and local cloud-init tasks. |
| `ansible/setup_folders.yml` | Platform | Creates and verifies the vCenter folder hierarchy. |

## Ownership Rules

- New roles must choose exactly one primary category in this document when they
  are added.
- Shared prerequisites belong in Base or Platform roles; concrete host purpose
  belongs in Workloads, Runner, or Networking roles.
- Playbooks may compose multiple categories, but their owner should reflect the
  workflow they primarily serve.
- Legacy roles should not receive new behavior unless the change explicitly
  keeps compatibility while replacing or removing the legacy path.
- Role rewrites are outside the scope of this ownership map. Use this document
  to guide future organization and migration work.
