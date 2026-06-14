import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
import socket

from homelab_gitops.domain.doctor import DoctorService
from homelab_gitops.cli.core_commands.doctor import doctor_command
from homelab_gitops.drivers.exceptions import PrerequisiteError

runner = CliRunner()

class TestDoctorService:
    @patch('homelab_gitops.domain.doctor.vCenterDriver')
    @patch('homelab_gitops.domain.doctor.TechnitiumDriver')
    @patch('homelab_gitops.domain.doctor.OPNsenseDriver')
    @patch('homelab_gitops.domain.doctor.TofuDriver')
    @patch('homelab_gitops.domain.doctor.socket.gethostbyname')
    def test_run_diagnostics_all_pass(self, mock_gethostbyname, mock_tofu, mock_opnsense, mock_technitium, mock_vcenter):
        # Setup mocks
        mock_vcenter_instance = mock_vcenter.return_value
        mock_vcenter_instance.validate.return_value = True
        
        mock_technitium_instance = mock_technitium.return_value
        mock_technitium_instance.validate.return_value = True
        
        mock_opnsense_instance = mock_opnsense.return_value
        mock_opnsense_instance.validate.return_value = True
        
        mock_tofu_instance = mock_tofu.return_value
        mock_tofu_instance.validate.return_value = True
        
        mock_gethostbyname.return_value = "1.1.1.1"

        service = DoctorService()
        results = service.run_diagnostics()

        assert results["vcenter"]["status"] == "pass"
        assert "latency" in results["vcenter"]
        
        assert results["technitium"]["status"] == "pass"
        assert "latency" in results["technitium"]
        
        assert results["opnsense"]["status"] == "pass"
        assert "latency" in results["opnsense"]
        
        assert results["tofu"]["status"] == "pass"
        assert "latency" in results["tofu"]
        
        assert results["dns"]["status"] == "pass"
        assert "latency" in results["dns"]

    @patch('homelab_gitops.domain.doctor.vCenterDriver')
    @patch('homelab_gitops.domain.doctor.TechnitiumDriver')
    @patch('homelab_gitops.domain.doctor.OPNsenseDriver')
    @patch('homelab_gitops.domain.doctor.TofuDriver')
    @patch('homelab_gitops.domain.doctor.socket.gethostbyname')
    def test_run_diagnostics_with_failures(self, mock_gethostbyname, mock_tofu, mock_opnsense, mock_technitium, mock_vcenter):
        # Setup mocks
        mock_vcenter_instance = mock_vcenter.return_value
        mock_vcenter_instance.validate.side_effect = PrerequisiteError("vCenter unreachable")
        
        mock_technitium_instance = mock_technitium.return_value
        mock_technitium_instance.validate.side_effect = Exception("Unknown error")
        
        mock_opnsense_instance = mock_opnsense.return_value
        mock_opnsense_instance.validate.return_value = True
        
        mock_tofu_instance = mock_tofu.return_value
        mock_tofu_instance.validate.return_value = True
        
        mock_gethostbyname.side_effect = socket.error("DNS resolution failed")

        service = DoctorService()
        results = service.run_diagnostics()

        assert results["vcenter"]["status"] == "fail"
        assert results["vcenter"]["error"] == "vCenter unreachable"
        
        assert results["technitium"]["status"] == "fail"
        assert results["technitium"]["error"] == "Unknown error"
        
        assert results["opnsense"]["status"] == "pass"
        
        assert results["tofu"]["status"] == "pass"
        
        assert results["dns"]["status"] == "fail"
        assert results["dns"]["error"] == "DNS resolution failed"

class TestDoctorCLI:
    @patch('homelab_gitops.cli.core_commands.doctor.DoctorService')
    def test_doctor_command_success(self, mock_doctor_service):
        mock_instance = mock_doctor_service.return_value
        mock_instance.run_diagnostics.return_value = {
            "vcenter": {"status": "pass", "latency": 0.1},
            "dns": {"status": "fail", "error": "Timeout"}
        }

        import typer
        app = typer.Typer()
        app.command(name="doctor")(doctor_command)

        result = runner.invoke(app, [])
        
        assert result.exit_code == 0
        assert "System Diagnostics" in result.stdout
        assert "Vcenter" in result.stdout
        assert "PASS" in result.stdout
        assert "Dns" in result.stdout
        assert "FAIL" in result.stdout
        assert "Timeout" in result.stdout

    @patch('homelab_gitops.cli.core_commands.doctor.DoctorService')
    def test_doctor_command_exception(self, mock_doctor_service):
        mock_instance = mock_doctor_service.return_value
        mock_instance.run_diagnostics.side_effect = Exception("Critical failure")

        import typer
        app = typer.Typer()
        app.command(name="doctor")(doctor_command)

        result = runner.invoke(app, [])
        
        assert result.exit_code == 1
        assert "Diagnostics failed: Critical failure" in result.stdout
