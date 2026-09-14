#!/usr/bin/env python3
"""Derive the machine-readable estate inventory JSON from its YAML source.

Authority
---------
``config/estate_inventory.yaml`` is the authoritative, hand-maintained,
version-controlled record of the estate. This script does **not** produce it and
must never overwrite it.

Until 2026-09-13 this script *was* the estate: every host, MAC, IP, GPU model
and VRAM figure lived here as a Python dict literal, and it wrote out a
``config/estate_inventory.yaml`` that declared itself authoritative while being
gitignored. The record could therefore not be reviewed, diffed or blamed, and
correcting a fact meant editing a script. The drift that exposed it was real:
srv-04 was still recorded as a dual Intel Arc Pro B65 machine months after one
card was replaced, and the surviving B65's VRAM was recorded as 16 GB when the
card reports 32,656 MiB.

The facts now live in the YAML. This script only reads, validates and derives.

Outputs
-------
``config/estate_inventory.json`` -- a derived build artefact, gitignored,
byte-identical in content to the YAML. Consumers that want JSON read it;
consumers that want the truth read the YAML.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parent.parent
SOURCE_YAML = REPO_ROOT / "config" / "estate_inventory.yaml"
DERIVED_JSON = REPO_ROOT / "config" / "estate_inventory.json"

REQUIRED_TOP_LEVEL = (
    "metadata",
    "network",
    "physical_servers",
    "storage",
    "virtual_machines",
    "kubernetes_clusters",
    "docker_hosts",
    "discrepancies_and_resolutions",
)

REQUIRED_METADATA = (
    "title",
    "domain",
    "site_cidr",
    "last_updated",
    "authoritative_source",
    "version",
)


class EstateValidationError(Exception):
    """The estate source file is missing structure the consumers rely on."""


def load_estate(path: Path = SOURCE_YAML) -> dict[str, Any]:
    """Load and validate the authoritative estate record."""
    if not path.exists():
        raise EstateValidationError(
            f"{path} does not exist. It is the authoritative estate record and is "
            "tracked in git -- it is not generated, so it cannot be rebuilt by "
            "re-running this script. Restore it from version control."
        )

    with path.open() as handle:
        estate = yaml.safe_load(handle)

    if not isinstance(estate, dict):
        raise EstateValidationError(f"{path} did not parse to a mapping.")

    missing = [key for key in REQUIRED_TOP_LEVEL if key not in estate]
    if missing:
        raise EstateValidationError(
            f"{path} is missing required top-level sections: {', '.join(missing)}"
        )

    metadata = estate["metadata"]
    if not isinstance(metadata, dict):
        raise EstateValidationError(f"{path}: metadata must be a mapping.")

    missing_meta = [key for key in REQUIRED_METADATA if key not in metadata]
    if missing_meta:
        raise EstateValidationError(
            f"{path}: metadata is missing required keys: {', '.join(missing_meta)}"
        )

    declared = metadata["authoritative_source"]
    expected = "config/estate_inventory.yaml"
    if declared != expected:
        raise EstateValidationError(
            f"{path}: metadata.authoritative_source is {declared!r}, expected "
            f"{expected!r}. The file that claims authority must be the file that "
            "holds it and is tracked in git."
        )

    _validate_hosts(estate["physical_servers"], path)
    return estate


def _validate_hosts(hosts: Any, path: Path) -> None:
    if not isinstance(hosts, list) or not hosts:
        raise EstateValidationError(f"{path}: physical_servers must be a non-empty list.")

    seen: set[str] = set()
    for host in hosts:
        host_id = host.get("id")
        if not host_id:
            raise EstateValidationError(f"{path}: a physical_servers entry has no id.")
        if host_id in seen:
            raise EstateValidationError(f"{path}: duplicate physical_servers id {host_id!r}.")
        seen.add(host_id)

        # A GPU's address and its VRAM are the two facts capacity planning reads.
        # A silently absent VRAM figure is how 16-vs-32 GB drift survives.
        for gpu in host.get("hardware", {}).get("gpus", []):
            if "device" not in gpu:
                raise EstateValidationError(
                    f"{path}: {host_id} has a GPU entry with no PCI device address."
                )
            model = gpu.get("model", "")
            is_igpu = "iGPU" in model or "integrated" in model.lower()
            if not is_igpu and "vram" not in gpu:
                raise EstateValidationError(
                    f"{path}: {host_id} GPU {gpu['device']} records no vram. "
                    "Discrete GPUs must carry a VRAM figure."
                )


def derive_json(estate: dict[str, Any], path: Path = DERIVED_JSON) -> None:
    """Write the derived JSON projection of the estate record."""
    payload = dict(estate)
    metadata = dict(payload["metadata"])
    metadata["derived_from"] = "config/estate_inventory.yaml"
    metadata["note"] = (
        "Generated build artefact -- do not edit. Correct facts in "
        "config/estate_inventory.yaml and re-run scripts/build_estate_inventory.py."
    )
    payload["metadata"] = metadata

    with path.open("w") as handle:
        json.dump(payload, handle, indent=2)
        handle.write("\n")


def main() -> int:
    try:
        estate = load_estate()
    except EstateValidationError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    derive_json(estate)
    hosts = len(estate["physical_servers"])
    vms = len(estate["virtual_machines"])
    print(f"Read authoritative estate from {SOURCE_YAML} ({hosts} physical hosts, {vms} VMs)")
    print(f"Wrote derived JSON to {DERIVED_JSON}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
