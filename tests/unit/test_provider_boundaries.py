"""Provider boundary guardrails for domain workflow modules."""

import ast
from pathlib import Path


WORKFLOW_MODULES = (
    Path("src/homelab_gitops/domain/workflows.py"),
    Path("src/homelab_gitops/domain/immutable_workflow.py"),
)

READ_ONLY_FLOW_MODULES = (
    Path("src/homelab_gitops/domain/status.py"),
    Path("src/homelab_gitops/domain/doctor.py"),
    Path("src/homelab_gitops/cli/core_commands/status.py"),
    Path("src/homelab_gitops/cli/core_commands/doctor.py"),
)


def test_workflow_modules_do_not_import_concrete_drivers():
    """Workflow orchestration should receive providers instead of importing drivers."""
    violations = []

    for module_path in WORKFLOW_MODULES:
        tree = ast.parse(module_path.read_text(), filename=str(module_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("homelab_gitops.drivers") or node.module.startswith(
                    "homelab_gitops.immutable.drivers"
                ):
                    violations.append(f"{module_path}:{node.lineno} imports {node.module}")

    assert violations == []


def test_status_and_doctor_flows_do_not_import_concrete_drivers():
    """Read-only flows should use provider adapters instead of concrete drivers."""
    violations = []

    for module_path in READ_ONLY_FLOW_MODULES:
        tree = ast.parse(module_path.read_text(), filename=str(module_path))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                if node.module.startswith("homelab_gitops.drivers") or node.module.startswith(
                    "homelab_gitops.immutable.drivers"
                ):
                    violations.append(f"{module_path}:{node.lineno} imports {node.module}")

    assert violations == []
