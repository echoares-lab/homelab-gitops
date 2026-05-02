# Unified GitOps Template Pipeline

A professional-grade automation framework for building, provisioning, and configuring a diverse inventory of Ubuntu and VMware Photon OS nodes on vSphere.

## 🚀 Key Features
*   **Unified Orchestration:** A single script (`manage.sh`) manages the entire lifecycle across different OS distributions.
*   **Golden Image Strategy:** Automated builds via **Packer** ensure every node starts from a secure, high-performance baseline in the vCenter Content Library.
*   **Declarative Infrastructure:** Uses **OpenTofu** (Terraform) with **Workspace isolation** to manage virtual hardware state idempotently.
*   **Tag-Based Configuration:** Utilizes **Ansible Dynamic Inventory** to automatically discover and configure nodes based on vSphere tags (e.g., `tag_docker`, `tag_ubuntu`).
*   **Profile-Driven:** Deployment settings are centralized in readable YAML profiles (e.g., `config/profiles/photon-docker.yml`).

---

## 📖 Documentation
For detailed guides, please refer to the following documents:

*   **[Operations Runbook](./docs/RUNBOOK.md)**: Detailed step-by-step instructions for installation, building, deploying, and troubleshooting.
*   **[Architecture Design](./docs/DESIGN.md)**: High-level design diagrams and technical principles.
*   **[Development Roadmap](./docs/ROADMAP.md)**: Tracking of completed and future improvements.

---

## 🛠️ Quick Start

### 1. Configure Credentials
Copy the example secrets file and populate it with your vCenter details:
```bash
cp config/secrets.env.example config/secrets.env
# Edit config/secrets.env
```

### 2. Deploy a New Node
Deploy a Photon OS Docker node using the pre-defined profile. You can optionally specify the target ESXi host (defaults to `esxi-01...`):
```bash
./manage.sh all photon-docker 02 esxi-02.mgmt.plexplease.com
```
This single command will:
1.  **Lint** the infrastructure availability.
2.  **Deploy** the virtual hardware from the Content Library.
3.  **Tag** the VM with `photon` and `docker`.
4.  **Configure** the node with Docker CE and security hardening.

---

## 📂 Project Structure
*   `ansible/`: Dynamic inventory configuration and roles (`base`, `security`, `docker`).
*   `config/`: YAML deployment profiles and global secrets.
*   `docs/`: Detailed runbooks, design docs, and roadmaps.
*   `packer/`: Automated golden image build definitions.
*   `tofu/`: Declarative infrastructure-as-code (vSphere provider).
*   `scripts/`: Python-based pre-flight linting and initialization tools.

---

## ⚖️ Policies & Standards
See [GEMINI.md](./GEMINI.md) for detailed coding standards, linting requirements, and architectural rules governing this repository.
