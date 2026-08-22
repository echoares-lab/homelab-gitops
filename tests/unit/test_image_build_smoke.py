from pathlib import Path

import pytest

from scripts.validate_image_build_inputs import (
    ImageBuildValidationError,
    ImageBuildValidator,
)


def write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def test_validator_runs_packer_validation_for_each_template(tmp_path, monkeypatch):
    write(
        tmp_path / "packer" / "ubuntu2404.pkr.hcl",
        """
variable "vcenter_server" {
  type = string
}
source "vsphere-iso" "ubuntu2404" {
  vcenter_server = var.vcenter_server
}
""",
    )
    write(
        tmp_path / "packer" / "photon.pkr.hcl",
        """
variable "network" {
  type = string
}
source "vsphere-iso" "photon" {
  network = var.network
}
""",
    )

    runs = []

    def fake_run(command, cwd, text, capture_output):
        runs.append((command, cwd))

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(
        "scripts.validate_image_build_inputs.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr("scripts.validate_image_build_inputs.subprocess.run", fake_run)
    monkeypatch.setattr(ImageBuildValidator, "_validate_butane_transpilation", lambda self: None)

    result = ImageBuildValidator(tmp_path).validate()

    assert result.packer_templates_validated == 2
    assert runs == [
        (["packer", "init", "photon.pkr.hcl"], tmp_path / "packer"),
        (
            ["packer", "validate", "-var", "network=VM Network", "photon.pkr.hcl"],
            tmp_path / "packer",
        ),
        (["packer", "init", "ubuntu2404.pkr.hcl"], tmp_path / "packer"),
        (
            [
                "packer",
                "validate",
                "-var",
                "vcenter_server=vcenter.example.test",
                "ubuntu2404.pkr.hcl",
            ],
            tmp_path / "packer",
        ),
    ]


def test_validator_fails_when_template_declares_unknown_variable(tmp_path, monkeypatch):
    write(
        tmp_path / "packer" / "custom.pkr.hcl",
        """
variable "unsupported" {
  type = string
}
""",
    )

    # `validate()` runs `packer init <template>` BEFORE it inspects the
    # template's variables, so without this stub the test shelled out to the
    # real packer on the CI runner (plugin fetch over the network: 16s for this
    # file, tipping the Tier-2 suite past its 10s cap). A unit test never
    # spawns a process.
    runs = []

    def fake_run(command, cwd, text, capture_output):
        runs.append(command)

        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    monkeypatch.setattr(
        "scripts.validate_image_build_inputs.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr("scripts.validate_image_build_inputs.subprocess.run", fake_run)

    with pytest.raises(ImageBuildValidationError, match="No smoke value configured"):
        ImageBuildValidator(tmp_path).validate()

    assert runs == [["packer", "init", "custom.pkr.hcl"]]


def test_validator_exercises_butane_transpilation(tmp_path, monkeypatch):
    write(tmp_path / "packer" / "empty.pkr.hcl", "")

    calls = []

    def fake_run(command, cwd, text, capture_output):
        class Result:
            returncode = 0
            stdout = ""
            stderr = ""

        return Result()

    class FakeTranspiler:
        def transpile(self, profile):
            calls.append(profile)
            return '{"ignition": {"version": "3.4.0"}}'

    monkeypatch.setattr(
        "scripts.validate_image_build_inputs.shutil.which",
        lambda name: f"/usr/bin/{name}",
    )
    monkeypatch.setattr("scripts.validate_image_build_inputs.subprocess.run", fake_run)
    monkeypatch.setattr("scripts.validate_image_build_inputs.ButaneTranspiler", FakeTranspiler)

    result = ImageBuildValidator(tmp_path).validate()

    assert result.butane_profiles_validated == 1
    assert calls[0].name == "fcos-smoke"
    assert calls[0].deployment["tags"] == ["fcos", "k3s_server"]
