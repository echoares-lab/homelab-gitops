from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_packer_http_paths_follow_image_build_layout():
    ubuntu_template = (ROOT / "packer/ubuntu2404.pkr.hcl").read_text()
    fcos_template = (ROOT / "packer/fcos.pkr.hcl").read_text()

    assert 'http_directory = "${path.root}/http/ubuntu2404"' in ubuntu_template
    assert 'http_directory = "${path.root}/../build/http/fcos"' in fcos_template
    assert "/http/fcos/installed.ign" not in fcos_template
    assert "/installed.ign" in fcos_template


def test_no_generated_ignition_is_tracked_with_packer_http_sources():
    assert not list((ROOT / "packer/http/fcos").glob("*.ign"))
