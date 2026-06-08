import pytest
from unittest.mock import Mock, patch, MagicMock
from services.wrappers.packer_wrapper import PackerWrapper


class TestPackerWrapperInit:
    @patch("shutil.which")
    def test_init_validates_packer(self, mock_which):
        mock_which.return_value = "/usr/bin/packer"
        wrapper = PackerWrapper()
        mock_which.assert_called_with("packer")


class TestPackerWrapperBuild:
    @patch("subprocess.run")
    @patch("shutil.which")
    def test_build_executes_packer_build(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/packer"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = PackerWrapper()
        result = wrapper.build("ubuntu-2404")

        assert result is True
        mock_run.assert_called_once()
        args, _ = mock_run.call_args
        cmd = args[0]
        assert cmd[0] == "packer"
        assert "build" in cmd
        assert "packer/ubuntu-2404.pkr.hcl" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_build_handles_photon_target(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/packer"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = PackerWrapper()
        wrapper.build("photon-docker")

        args, _ = mock_run.call_args
        cmd = args[0]
        assert "packer/photon-docker.pkr.hcl" in cmd

    @patch("subprocess.run")
    @patch("shutil.which")
    def test_build_returns_false_on_failure(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/packer"
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_run.return_value = mock_result

        wrapper = PackerWrapper()
        result = wrapper.build("ubuntu-2404")

        assert result is False


class TestPackerWrapperValidateTemplate:
    @patch("subprocess.run")
    @patch("shutil.which")
    def test_validate_template_checks_template(self, mock_which, mock_run):
        mock_which.return_value = "/usr/bin/packer"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        wrapper = PackerWrapper()
        result = wrapper.validate_template("packer/ubuntu-2404.pkr.hcl")

        assert result is True
        args, _ = mock_run.call_args
        cmd = args[0]
        assert "validate" in cmd
        assert "packer/ubuntu-2404.pkr.hcl" in cmd
