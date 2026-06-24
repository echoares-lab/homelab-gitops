#!/usr/bin/env python3
"""Smoke-validate image build inputs without deploying infrastructure."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from homelab_gitops.domain.models import NodeProfile  # noqa: E402
from homelab_gitops.immutable.transpilers.butane import ButaneTranspiler  # noqa: E402


VARIABLE_PATTERN = re.compile(r'^\s*variable\s+"([^"]+)"\s*\{', re.MULTILINE)

SMOKE_VAR_VALUES = {
    "cluster": "Cluster",
    "datacenter": "Datacenter",
    "datastore": "Datastore",
    "name": "image-smoke",
    "network": "VM Network",
    "photon_iso_checksum": (
        "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    ),
    "photon_iso_url": "https://example.test/photon.iso",
    "profile_name": "fcos-smoke",
    "ssh_password": "packer-smoke-password",
    "ssh_username": "packer",
    "ubuntu_iso_checksum": (
        "sha256:0000000000000000000000000000000000000000000000000000000000000000"
    ),
    "ubuntu_iso_url": "https://example.test/ubuntu.iso",
    "vcenter_password": "packer-smoke-password",
    "vcenter_server": "vcenter.example.test",
    "vcenter_username": "administrator@example.test",
    "vm_name": "image-smoke",
}


class ImageBuildValidationError(Exception):
    """Raised when image build input validation fails."""


@dataclass
class ImageBuildValidationResult:
    packer_templates_validated: int = 0
    butane_profiles_validated: int = 0


class ImageBuildValidator:
    """Validate local image build inputs without starting a build."""

    def __init__(self, repo_root: Path | str | None = None):
        self.repo_root = Path(repo_root or ROOT).resolve()
        self.packer_dir = self.repo_root / "packer"

    def validate(self) -> ImageBuildValidationResult:
        self._require_tool("packer")
        self._require_tool("butane")

        result = ImageBuildValidationResult()
        for template in self._packer_templates():
            self._validate_packer_template(template)
            result.packer_templates_validated += 1

        self._validate_butane_transpilation()
        result.butane_profiles_validated += 1

        return result

    def _packer_templates(self) -> list[Path]:
        if not self.packer_dir.exists():
            raise ImageBuildValidationError(
                f"Packer directory not found: {self._display(self.packer_dir)}"
            )

        templates = sorted(self.packer_dir.glob("*.pkr.hcl"))
        if not templates:
            raise ImageBuildValidationError(
                f"No Packer templates found under {self._display(self.packer_dir)}"
            )
        return templates

    def _validate_packer_template(self, template: Path) -> None:
        template_name = template.name
        self._run(["packer", "init", template_name], cwd=self.packer_dir)

        validate_command = ["packer", "validate"]
        for variable_name in self._template_variables(template):
            try:
                value = SMOKE_VAR_VALUES[variable_name]
            except KeyError as exc:
                raise ImageBuildValidationError(
                    "No smoke value configured for Packer variable "
                    f"{variable_name!r} in {self._display(template)}"
                ) from exc
            validate_command.extend(["-var", f"{variable_name}={value}"])

        validate_command.append(template_name)
        self._run(validate_command, cwd=self.packer_dir)

    def _template_variables(self, template: Path) -> list[str]:
        content = template.read_text(encoding="utf-8")
        return sorted(set(VARIABLE_PATTERN.findall(content)))

    def _validate_butane_transpilation(self) -> None:
        profile = NodeProfile(
            name="fcos-smoke",
            vcenter={
                "datacenter": "Datacenter",
                "cluster": "Cluster",
                "datastore": "Datastore",
                "network": "VM Network",
            },
            vm_specs={"cpu": 2, "memory": 2048, "disk": 20},
            deployment={
                "tags": ["fcos", "k3s_server"],
                "hostname": "fcos-smoke",
                "ip_address": "192.0.2.10",
                "ipv4_netmask": 24,
                "ipv4_gateway": "192.0.2.1",
                "dns_servers": ["192.0.2.53"],
            },
        )

        try:
            ignition = ButaneTranspiler().transpile(profile)
            json.loads(ignition)
        except Exception as exc:
            raise ImageBuildValidationError(
                f"Butane transpilation smoke validation failed: {exc}"
            ) from exc

    def _run(self, command: list[str], cwd: Path) -> None:
        result = subprocess.run(command, cwd=cwd, text=True, capture_output=True)
        if result.returncode != 0:
            output = "\n".join(
                part for part in (result.stdout.strip(), result.stderr.strip()) if part
            )
            raise ImageBuildValidationError(
                f"Command failed ({' '.join(command)}):\n{output or 'no output'}"
            )

    def _require_tool(self, tool: str) -> None:
        if not shutil.which(tool):
            raise ImageBuildValidationError(f"Required tool not found in PATH: {tool}")

    def _display(self, path: Path) -> str:
        try:
            return str(path.resolve().relative_to(self.repo_root))
        except ValueError:
            return str(path)


def main() -> int:
    try:
        result = ImageBuildValidator().validate()
    except ImageBuildValidationError as exc:
        print(f"image build smoke validation failed: {exc}", file=sys.stderr)
        return 1

    print(
        "image build smoke validation passed: "
        f"{result.packer_templates_validated} Packer template(s), "
        f"{result.butane_profiles_validated} Butane profile(s)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
