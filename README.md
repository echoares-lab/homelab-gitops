# Unified GitOps Template Pipeline

A professional-grade automation framework for building, provisioning, and configuring high-performance Ubuntu and VMware Photon OS nodes on vSphere.

## 🚀 Key Features
*   **Unified Orchestrator:** A single script (`manage.sh`) manages the entire lifecycle: Build, Deploy, Config, Test, and Destroy.
*   **Interactive Command Builder:** Running `./manage.sh` with no arguments launches a guided wizard to build and execute pipeline commands.
*   **Scaffolding Helpers:** Built-in wizards for creating Profiles, Roles, and Ansible Plays (`create-profile`, `create-role`, `create-play`).
*   **Optimized Golden Images:** All templates are pre-remediated to use VMware best practices: **PVSCSI** controllers, **VMXNET3** adapters, and Hardware Version **vmx-21**.
*   **Declarative Infrastructure:** Uses **OpenTofu** (Terraform) with **Workspace isolation** to manage virtual hardware state idempotently.
*   **Automated Verification:** Integrated **Pytest-Testinfra** suite validates OS hardening and service state immediately after deployment.
*   **Profile-Driven:** Centralized YAML profiles (`config/profiles/`) define the "Source of Truth" for every node.

---

## 📖 Documentation
For detailed guides, please refer to:
*   **[Operations Runbook](./docs/RUNBOOK.md)**: Installation, command usage, and troubleshooting.
*   **[Architecture Design](./docs/DESIGN.md)**: Workflow diagrams and hardware standards.
*   **[Development Roadmap](./docs/ROADMAP.md)**: Project status and milestones.

---

## 🛠️ Quick Start

### 1. Configure Credentials
```bash
cp config/secrets.env.example config/secrets.env
# Populate with your vCenter details
```

### 2. Deploy a New Node
Deploy a Photon OS Docker node targeting a specific host:
```bash
./manage.sh all photon-docker 02 esxi-01.mgmt.plexplease.com
```

This single command executes the full pipeline:
1.  **Lint:** Validates YAML schema and vCenter infrastructure.
2.  **Deploy:** Provisions vmx-21 hardware with OpenTofu.
3.  **Config:** Applies Ansible roles via dynamic tag-based discovery.
4.  **Test:** Runs Pytest-Testinfra E2E validation.

---

## 📂 Project Structure
*   `ansible/`: Roles and dynamic inventory configuration.
*   `config/`: YAML node profiles and global secrets.
*   `docs/`: Runbooks, designs, and roadmaps.
*   `packer/`: Golden image build definitions.
*   `tofu/`: Declarative HCL for vSphere provisioning.
*   `tests/`: Testinfra validation scripts.

---

## ⚖️ Policies & Standards
See [GEMINI.md](./GEMINI.md) for detailed coding standards and architectural rules.
