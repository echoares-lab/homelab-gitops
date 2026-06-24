from pathlib import Path

import pytest

from scripts.validate_gitops_manifests import ManifestValidationError, GitOpsManifestValidator


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validator_renders_nested_kustomizations(tmp_path: Path) -> None:
    write(
        tmp_path / "kubernetes" / "clusters" / "k3s-01" / "kustomization.yaml",
        """
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - config/namespaces.yaml
  - ../../platform/cert-manager/overlays/k3s-01
""",
    )
    write(
        tmp_path
        / "kubernetes"
        / "platform"
        / "cert-manager"
        / "overlays"
        / "k3s-01"
        / "kustomization.yaml",
        """
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - helmchart.yaml
""",
    )
    write(
        tmp_path / "kubernetes" / "clusters" / "k3s-01" / "config" / "namespaces.yaml",
        """
apiVersion: v1
kind: Namespace
metadata:
  name: cert-manager
""",
    )
    write(
        tmp_path
        / "kubernetes"
        / "platform"
        / "cert-manager"
        / "overlays"
        / "k3s-01"
        / "helmchart.yaml",
        """
apiVersion: helm.cattle.io/v1
kind: HelmChart
metadata:
  name: cert-manager
  namespace: kube-system
spec:
  chart: cert-manager
""",
    )

    result = GitOpsManifestValidator(tmp_path).validate()

    assert result.kustomizations_rendered == 2
    assert result.objects_validated == 2


def test_validator_reports_malformed_yaml(tmp_path: Path) -> None:
    write(
        tmp_path / "kubernetes" / "clusters" / "k3s-01" / "kustomization.yaml",
        """
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - bad.yaml
""",
    )
    write(
        tmp_path / "kubernetes" / "clusters" / "k3s-01" / "bad.yaml",
        "apiVersion: v1\nkind: Namespace\nmetadata: [broken\n",
    )

    with pytest.raises(ManifestValidationError, match="invalid YAML"):
        GitOpsManifestValidator(tmp_path).validate()


def test_validator_reports_missing_kubernetes_required_fields(tmp_path: Path) -> None:
    write(
        tmp_path / "kubernetes" / "clusters" / "k3s-01" / "kustomization.yaml",
        """
apiVersion: kustomize.config.k8s.io/v1beta1
kind: Kustomization
resources:
  - namespace.yaml
""",
    )
    write(
        tmp_path / "kubernetes" / "clusters" / "k3s-01" / "namespace.yaml",
        """
apiVersion: v1
metadata:
  name: missing-kind
""",
    )

    with pytest.raises(ManifestValidationError, match="missing required field: kind"):
        GitOpsManifestValidator(tmp_path).validate()
