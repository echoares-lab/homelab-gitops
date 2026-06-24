#!/usr/bin/env python3
"""Validate Kubernetes GitOps manifests and Kustomize resource graphs."""

from __future__ import annotations

import argparse
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


KUSTOMIZATION_FILENAMES = ("kustomization.yaml", "kustomization.yml")


class ManifestValidationError(Exception):
    """Raised when a GitOps manifest validation error is found."""


@dataclass
class ValidationResult:
    kustomizations_rendered: int = 0
    objects_validated: int = 0
    manifest_files_validated: int = 0
    rendered_kustomizations: set[Path] = field(default_factory=set)
    validated_manifest_files: set[Path] = field(default_factory=set)
    validated_objects: set[tuple[Path, int]] = field(default_factory=set)


class GitOpsManifestValidator:
    """Validate kustomization resources and the Kubernetes objects they render."""

    def __init__(self, repo_root: Path | str | None = None, gitops_root: Path | str = "kubernetes"):
        self.repo_root = Path(repo_root or Path(__file__).resolve().parents[1]).resolve()
        self.gitops_root = (self.repo_root / gitops_root).resolve()
        self.result = ValidationResult()

    def validate(self) -> ValidationResult:
        if not self.gitops_root.exists():
            raise ManifestValidationError(f"GitOps root does not exist: {self._display(self.gitops_root)}")
        if not self.gitops_root.is_dir():
            raise ManifestValidationError(f"GitOps root is not a directory: {self._display(self.gitops_root)}")

        kustomizations = sorted(
            path
            for path in self.gitops_root.rglob("*")
            if path.name in KUSTOMIZATION_FILENAMES and path.is_file()
        )
        if not kustomizations:
            raise ManifestValidationError(
                f"No kustomization.yaml files found under {self._display(self.gitops_root)}"
            )

        for kustomization in kustomizations:
            self._render_kustomization(kustomization)

        return self.result

    def _render_kustomization(self, path: Path) -> None:
        path = path.resolve()
        if path in self.result.rendered_kustomizations:
            return

        documents = self._load_yaml_documents(path)
        if len(documents) != 1:
            raise ManifestValidationError(
                f"{self._display(path)} must contain exactly one Kustomization document"
            )

        kustomization = documents[0]
        if not isinstance(kustomization, dict):
            raise ManifestValidationError(f"{self._display(path)} must be a YAML mapping")
        self._require_string(kustomization, "apiVersion", path)
        kind = self._require_string(kustomization, "kind", path)
        if kind != "Kustomization":
            raise ManifestValidationError(f"{self._display(path)} kind must be Kustomization")

        resources = kustomization.get("resources", [])
        if resources is None:
            resources = []
        if not isinstance(resources, list):
            raise ManifestValidationError(f"{self._display(path)} resources must be a list")

        self.result.rendered_kustomizations.add(path)
        self.result.kustomizations_rendered = len(self.result.rendered_kustomizations)

        for resource in resources:
            if not isinstance(resource, str) or not resource:
                raise ManifestValidationError(
                    f"{self._display(path)} resources entries must be non-empty strings"
                )
            resource_path = (path.parent / resource).resolve()
            self._validate_resource(resource_path, path)

    def _validate_resource(self, resource_path: Path, owner: Path) -> None:
        if not self._is_under_gitops_root(resource_path):
            raise ManifestValidationError(
                f"{self._display(owner)} references path outside GitOps root: {resource_path}"
            )
        if not resource_path.exists():
            raise ManifestValidationError(
                f"{self._display(owner)} references missing resource: {self._display(resource_path)}"
            )

        if resource_path.is_dir():
            kustomization = self._find_kustomization(resource_path)
            if kustomization is None:
                raise ManifestValidationError(
                    f"{self._display(owner)} references directory without kustomization.yaml: "
                    f"{self._display(resource_path)}"
                )
            self._render_kustomization(kustomization)
            return

        self._validate_manifest_file(resource_path)

    def _validate_manifest_file(self, path: Path) -> None:
        path = path.resolve()
        if path in self.result.validated_manifest_files:
            return

        documents = self._load_yaml_documents(path)
        self.result.validated_manifest_files.add(path)
        self.result.manifest_files_validated = len(self.result.validated_manifest_files)

        for index, document in enumerate(documents, start=1):
            if document is None:
                continue
            self._validate_kubernetes_object(document, path, index)
            self.result.validated_objects.add((path, index))
            self.result.objects_validated = len(self.result.validated_objects)

    def _validate_kubernetes_object(self, document: Any, path: Path, index: int) -> None:
        location = f"{self._display(path)} document {index}"
        if not isinstance(document, dict):
            raise ManifestValidationError(f"{location} must be a YAML mapping")

        self._require_string(document, "apiVersion", path, index)
        kind = self._require_string(document, "kind", path, index)

        if kind == "List":
            items = document.get("items")
            if not isinstance(items, list):
                raise ManifestValidationError(f"{location} kind List must include an items list")
            for item_index, item in enumerate(items, start=1):
                self._validate_kubernetes_object(item, path, item_index)
            return

        metadata = document.get("metadata")
        if not isinstance(metadata, dict):
            raise ManifestValidationError(f"{location} missing required field: metadata")
        self._require_string(metadata, "name", path, index, parent="metadata")

    def _load_yaml_documents(self, path: Path) -> list[Any]:
        try:
            with path.open(encoding="utf-8") as handle:
                return list(yaml.safe_load_all(handle))
        except yaml.YAMLError as exc:
            raise ManifestValidationError(f"{self._display(path)} invalid YAML: {exc}") from exc

    def _require_string(
        self,
        data: dict[str, Any],
        field_name: str,
        path: Path,
        index: int | None = None,
        parent: str | None = None,
    ) -> str:
        value = data.get(field_name)
        field_path = f"{parent}.{field_name}" if parent else field_name
        if not isinstance(value, str) or not value:
            location = self._display(path)
            if index is not None:
                location = f"{location} document {index}"
            raise ManifestValidationError(f"{location} missing required field: {field_path}")
        return value

    @staticmethod
    def _find_kustomization(directory: Path) -> Path | None:
        for filename in KUSTOMIZATION_FILENAMES:
            candidate = directory / filename
            if candidate.is_file():
                return candidate
        return None

    def _is_under_gitops_root(self, path: Path) -> bool:
        try:
            path.relative_to(self.gitops_root)
            return True
        except ValueError:
            return False

    def _display(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.repo_root))
        except ValueError:
            return str(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the parent of scripts/.",
    )
    parser.add_argument(
        "--gitops-root",
        default="kubernetes",
        help="GitOps manifest root relative to the repository root.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    validator = GitOpsManifestValidator(args.repo_root, args.gitops_root)
    try:
        result = validator.validate()
    except ManifestValidationError as exc:
        print(f"GitOps manifest validation failed: {exc}")
        return 1

    print("GitOps manifest validation passed")
    print(f"  Kustomizations rendered: {result.kustomizations_rendered}")
    print(f"  Manifest files validated: {result.manifest_files_validated}")
    print(f"  Kubernetes objects validated: {result.objects_validated}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
