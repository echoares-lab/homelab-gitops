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


def velero_helm_values() -> dict:
    documents = load_yaml_documents(
        PLATFORM_ROOT / "velero" / "overlays" / "k3s-01" / "helmchart.yaml"
    )
    helmchart = next(document for document in documents if document.get("kind") == "HelmChart")
    return yaml.safe_load(helmchart["spec"]["valuesContent"])


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


def observability_helmchart(name: str) -> dict:
    for path in (PLATFORM_ROOT / "observability" / "overlays" / "k3s-01").glob("*.yaml"):
        for document in load_yaml_documents(path):
            if document.get("kind") == "HelmChart" and document.get("metadata", {}).get("name") == name:
                return document
    raise AssertionError(f"Missing observability HelmChart: {name}")


def helmchart_values(name: str) -> dict:
    return yaml.safe_load(observability_helmchart(name)["spec"]["valuesContent"])


def test_observability_kustomization_includes_loki_and_alloy() -> None:
    resources = kustomization_resources(
        PLATFORM_ROOT / "observability" / "overlays" / "k3s-01" / "kustomization.yaml"
    )

    assert "loki-helmchart.yaml" in resources
    assert "alloy-helmchart.yaml" in resources


def test_loki_uses_pvc_storage_and_seven_day_retention() -> None:
    helmchart = observability_helmchart("loki")
    values = yaml.safe_load(helmchart["spec"]["valuesContent"])

    assert helmchart["spec"]["repo"] == "https://grafana-community.github.io/helm-charts"
    assert helmchart["spec"]["chart"] == "loki"
    assert helmchart["spec"]["targetNamespace"] == "observability"
    assert values["deploymentMode"] == "Monolithic"
    assert values["loki"]["storage"]["type"] == "filesystem"
    assert values["loki"]["limits_config"]["retention_period"] == "7d"
    assert values["loki"]["compactor"]["retention_enabled"] is True
    assert values["singleBinary"]["replicas"] == 1
    assert values["singleBinary"]["persistence"]["storageClass"] == "storage-standard"
    assert values["singleBinary"]["persistence"]["size"] == "20Gi"


def test_alloy_collects_pod_logs_and_kubernetes_events() -> None:
    helmchart = observability_helmchart("alloy")
    values = yaml.safe_load(helmchart["spec"]["valuesContent"])
    config = values["alloy"]["configMap"]["content"]

    assert helmchart["spec"]["repo"] == "https://grafana.github.io/helm-charts"
    assert helmchart["spec"]["chart"] == "alloy"
    assert helmchart["spec"]["targetNamespace"] == "observability"
    assert values["controller"]["type"] == "deployment"
    assert 'discovery.kubernetes "pods"' in config
    assert 'loki.source.kubernetes "pods"' in config
    assert 'loki.source.kubernetes_events "cluster_events"' in config
    assert 'loki.write "default"' in config
    assert "http://loki-gateway.observability.svc.cluster.local/loki/api/v1/push" in config


def test_alloy_relabels_pod_logs_for_service_queries() -> None:
    values = helmchart_values("alloy")
    config = values["alloy"]["configMap"]["content"]

    assert 'discovery.relabel "pod_logs"' in config
    assert "targets    = discovery.relabel.pod_logs.output" in config
    assert 'target_label  = "namespace"' in config
    assert 'target_label  = "pod"' in config
    assert 'target_label  = "container"' in config
    assert 'target_label  = "app"' in config
    assert 'target_label  = "service"' in config
    assert 'target_label  = "component"' in config
    assert 'target_label  = "part_of"' in config
    assert "__meta_kubernetes_pod_label_app_kubernetes_io_name" in config
    assert "__meta_kubernetes_pod_label_app_kubernetes_io_component" in config
    assert "__meta_kubernetes_pod_label_app_kubernetes_io_part_of" in config


def test_grafana_has_loki_datasource() -> None:
    values = helmchart_values("kube-prometheus-stack")

    datasources = values["grafana"]["additionalDataSources"]

    assert {
        "name": "Loki",
        "type": "loki",
        "access": "proxy",
        "url": "http://loki-gateway.observability.svc.cluster.local",
    } in datasources


def test_alertmanager_webhook_targets_apprise_alerts_tag() -> None:
    document = load_yaml_documents(
        PLATFORM_ROOT
        / "apprise"
        / "overlays"
        / "k3s-01"
        / "alertmanager-webhook-config.yaml"
    )[0]

    server_source = document["data"]["server.py"]

    assert '"tag": "alerts"' in server_source


def test_velero_metrics_are_scraped_by_platform_prometheus() -> None:
    metrics = velero_helm_values()["metrics"]

    assert metrics["serviceMonitor"]["enabled"] is True
    assert metrics["serviceMonitor"]["additionalLabels"]["release"] == "kube-prometheus-stack"


def test_velero_has_failure_and_stale_backup_alerts() -> None:
    prometheus_rule = velero_helm_values()["metrics"]["prometheusRule"]
    alerts = {rule["alert"]: rule for rule in prometheus_rule["spec"]}

    assert prometheus_rule["enabled"] is True
    assert prometheus_rule["additionalLabels"]["release"] == "kube-prometheus-stack"
    assert {"VeleroBackupFailed", "VeleroBackupStale"}.issubset(alerts)
    assert "velero_backup_failure_total" in alerts["VeleroBackupFailed"]["expr"]
    assert "velero_backup_partial_failure_total" in alerts["VeleroBackupFailed"]["expr"]
    assert "velero_backup_validation_failure_total" in alerts["VeleroBackupFailed"]["expr"]
    assert "velero_backup_last_successful_timestamp" in alerts["VeleroBackupStale"]["expr"]
    assert 'schedule="platform-namespace-daily"' in alerts["VeleroBackupStale"]["expr"]
    assert "absent(" in alerts["VeleroBackupStale"]["expr"]
    assert "90000" in alerts["VeleroBackupStale"]["expr"]
    assert alerts["VeleroBackupStale"]["for"] == "1h"
