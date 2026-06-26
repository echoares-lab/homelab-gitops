from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
K3S_ROOT = REPO_ROOT / "kubernetes" / "clusters" / "k3s-01"
PLATFORM_ROOT = REPO_ROOT / "kubernetes" / "platform"
WORKLOAD_ROOT = REPO_ROOT / "kubernetes" / "workloads"


def load_yaml_documents(path: Path) -> list[dict]:
    return [
        document
        for document in yaml.safe_load_all(path.read_text(encoding="utf-8"))
        if isinstance(document, dict)
    ]


def kustomization_resources(path: Path) -> set[str]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    return set(document.get("resources", []))


def test_k3s_cluster_wires_required_platform_epics() -> None:
    resources = kustomization_resources(K3S_ROOT / "kustomization.yaml")

    assert "../../platform/velero/overlays/k3s-01" in resources
    assert "../../platform/observability/overlays/k3s-01" in resources
    assert "../../platform/apprise/overlays/k3s-01" in resources
    assert "../../platform/cloudnative-pg/overlays/k3s-01" in resources
    assert "../../platform/platform-postgres/overlays/k3s-01" in resources
    assert "../../platform/authentik/overlays/k3s-01" in resources
    assert "../../workloads/home/sample-app/overlays/k3s-01" in resources


def test_k3s_namespace_baseline_covers_platform_readiness_domains() -> None:
    namespaces = {
        document["metadata"]["name"]
        for document in load_yaml_documents(K3S_ROOT / "config" / "namespaces.yaml")
        if document.get("kind") == "Namespace"
    }

    assert {
        "ingress",
        "cert-manager",
        "external-secrets",
        "observability",
        "backup",
        "database",
        "identity",
        "notifications",
    }.issubset(namespaces)


def test_platform_kustomizations_exist_for_ready_cluster_services() -> None:
    for relative_path in [
        "velero/overlays/k3s-01",
        "observability/overlays/k3s-01",
        "apprise/overlays/k3s-01",
        "cloudnative-pg/overlays/k3s-01",
        "platform-postgres/overlays/k3s-01",
        "authentik/overlays/k3s-01",
    ]:
        assert (PLATFORM_ROOT / relative_path / "kustomization.yaml").is_file()


def test_sample_workload_template_declares_platform_contract() -> None:
    overlay = WORKLOAD_ROOT / "home" / "sample-app" / "overlays" / "k3s-01"
    resources = kustomization_resources(overlay / "kustomization.yaml")

    assert {"namespace.yaml", "deployment.yaml", "service.yaml", "ingress.yaml"}.issubset(resources)
    assert (WORKLOAD_ROOT / "home" / "sample-app" / "README.md").is_file()


def test_helmchart_values_content_is_valid_yaml() -> None:
    for path in (REPO_ROOT / "kubernetes").rglob("*.yaml"):
        for document in load_yaml_documents(path):
            if document.get("kind") != "HelmChart":
                continue
            values_content = document.get("spec", {}).get("valuesContent")
            if values_content:
                assert yaml.safe_load(values_content) is not None, path


def test_observability_uses_standard_storage_tier_for_prometheus() -> None:
    documents = load_yaml_documents(PLATFORM_ROOT / "observability" / "overlays" / "k3s-01" / "helmchart.yaml")
    helmchart = next(document for document in documents if document.get("kind") == "HelmChart")
    values = yaml.safe_load(helmchart["spec"]["valuesContent"])

    volume_claim = values["prometheus"]["prometheusSpec"]["storageSpec"]["volumeClaimTemplate"]

    assert volume_claim["spec"]["storageClassName"] == "storage-standard"
