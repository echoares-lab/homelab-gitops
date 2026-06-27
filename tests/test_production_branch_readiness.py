from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_push_workflows_include_production_branch() -> None:
    workflow_paths = [
        REPO_ROOT / ".github" / "workflows" / "lint-and-unit-tests.yml",
        REPO_ROOT / ".github" / "workflows" / "smoke-test.yml",
        REPO_ROOT / ".github" / "workflows" / "integration-tests.yml",
    ]

    for workflow_path in workflow_paths:
        workflow = yaml.safe_load(workflow_path.read_text(encoding="utf-8"))
        on_config = workflow.get("on", workflow.get(True))
        push_config = on_config["push"]

        assert "production" in push_config["branches"], workflow_path


