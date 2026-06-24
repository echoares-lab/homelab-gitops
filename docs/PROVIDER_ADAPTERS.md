# Provider Adapter Boundaries

This document defines the minimal provider adapter boundary for workflows that
coordinate vCenter, OpenTofu, Ansible, Packer, DNS, secrets, and ACME. It is a
contract for future refactors, not a request to move existing driver code.

## Boundary Principles

Provider adapters are the only layer that should know how to call external
systems. They own CLI invocations, SDK clients, HTTP requests, authentication
handoff, retries, timeouts, output parsing, and provider-specific exception
translation.

Workflows own sequencing and policy. They should pass typed request data to
providers, combine provider results, and decide what phase comes next. Workflows
should not build provider command lines, parse provider-native JSON, open
provider SDK sessions, or read provider credentials directly.

Domain models and validators own repository-local intent. They should not
depend on concrete provider modules or environment variables for external
systems.

## Workflow Usage

Workflows should receive provider objects from their caller or from a narrow
factory at the application boundary. The existing `Workflow(profile, drivers)`
shape is the preferred direction: callers assemble the provider map, and the
workflow consumes capabilities by phase or role.

Provider construction belongs in CLI commands, application services, or a
dedicated factory. Avoid constructing concrete drivers inside workflow methods.
When secrets are needed to prepare provider input, resolve them through an
injected secrets provider before calling the mutating provider.

Provider methods should be named by capability, not by provider implementation
detail. A compatibility `execute(task)` method can remain while migration is in
progress, but new workflow-facing code should prefer explicit methods so
read-only and mutating operations are obvious at call sites.

## Method Classes

Read-only provider methods may contact external systems but must not change
remote state. They are safe for status, validation, planning, diagnostics, and
preflight checks.

Mutating provider methods create, update, delete, register, issue, store, or
otherwise change remote state. Workflows should call them only inside an
explicit lifecycle phase such as build, deploy, configure, destroy, issue, or
migrate.

`validate()` is read-only for every provider. It may verify tools, credentials,
or connectivity, but it must not remediate missing state.

## Provider Responsibilities

| Provider | Responsibilities | Non-responsibilities | Read-only methods | Mutating methods |
| :--- | :--- | :--- | :--- | :--- |
| vCenter | Discover VM facts, power state, guest IPs, content-library objects, host placement, tags, and destroy or power operations that are explicitly delegated to vCenter. | Deciding lifecycle order, translating node profiles into full VM desired state, managing OpenTofu state, or resolving credentials. | `validate`, `get_vm_info`, `list_vms`, `get_power_state`, `get_guest_ip`, `find_content_library_item` | `power_on`, `power_off`, `destroy_vm`, tag or folder mutations when explicitly required |
| OpenTofu | Initialize/select workspaces, plan, apply, destroy, read outputs, and report workspace drift for infrastructure modules. | Owning profile validation, choosing lifecycle stages, managing guest OS configuration, or embedding secrets beyond variables supplied by workflows. | `validate`, `init`, `list_workspaces`, `select_workspace`, `plan`, `get_status`, `output` | `create_workspace`, `apply`, `destroy` |
| Ansible | Run playbooks against resolved inventory and variables, support check-mode where requested, and report play recap/output. | Selecting business policy, discovering secrets, provisioning VM hardware, or mutating source-of-truth profile files. | `validate`, `check`, `syntax_check`, `list_hosts` | `run_playbook`, `configure_host` |
| Packer | Validate templates, build golden images, and publish build artifacts according to supplied variables. | Deciding whether an image is needed, managing VM lifecycle after image creation, or applying post-deploy OS configuration. | `validate`, `inspect_template`, `validate_template` | `build_image` |
| DNS | Manage authoritative DNS records and DNS-backed DHCP data through Technitium or another DNS provider, including ACME TXT records when delegated by certificate workflows. | Owning certificate issuance, choosing hostnames from profiles, or treating manually managed records as repository intent. | `validate`, `list_zones`, `get_record`, `list_records`, `export_backup` | `create_zone`, `delete_zone`, `upsert_record`, `delete_record`, `enable_dhcp`, `disable_dhcp` |
| Secrets | Resolve secret references from OpenBao, 1Password, or environment variables; store generated artifacts only when a workflow explicitly requests persistence. | Choosing which credentials a workflow needs, logging secret values, transforming infrastructure policy, or silently falling back from required secret refs. | `validate`, `get_secret`, `resolve_file` | `store_secret`, `store_document` |
| ACME | Register or load an ACME account, request DNS-01 challenges, answer challenges, finalize orders, and return certificate material. | Creating DNS records directly, storing certificates, deploying certificates to hosts, or deciding production versus staging policy outside supplied configuration. | `validate`, `get_directory`, `request_challenge` | `register_account`, `answer_challenge`, `finalize_order`, `fetch_certificate` |

## Current Driver Cross-check

The current drivers under `src/homelab_gitops/drivers` already expose the
external-system boundary, but several methods are still grouped behind
`execute(task)`. Current read-only behavior includes `validate()` across all
drivers, `TofuDriver.get_status()`, vCenter VM info lookup for test/status
tasks, Technitium list/get/export operations, OPNsense list/export operations,
and secret resolution.

Current mutating behavior includes `TofuDriver.execute()` for deploy/destroy,
`AnsibleDriver.execute()` for configuration runs, `PackerDriver.execute()` for
image builds, vCenter destroy and power actions, Technitium record/zone/DHCP
changes, OPNsense VLAN/firewall/interface/DHCP changes, `SecretsDriver`
storage helpers, and ACME registration/finalization.

Known cleanup target: `domain.workflows` and `domain.immutable_workflow`
construct `SecretsDriver` while preparing task variables. Future provider
boundary work should inject a secrets provider or pre-resolved secret values at
the workflow boundary instead of constructing concrete drivers inside workflow
methods.
