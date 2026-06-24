import pytest
from unittest.mock import patch, MagicMock
from typer.testing import CliRunner
import socket

from homelab_gitops.domain.doctor import DoctorService
from homelab_gitops.cli.core_commands.doctor import doctor_command
from homelab_gitops.drivers.exceptions import PrerequisiteError

runner = CliRunner()


class HealthCheckStub:
    def __init__(self, error=None):
        self.error = error
        self.calls = 0

    def validate(self):
        self.calls += 1
        if self.error:
            raise self.error
        return True

class TestDoctorService:
    def test_run_diagnostics_all_pass(self):
        health_checks = {
            "vcenter": HealthCheckStub(),
            "technitium": HealthCheckStub(),
            "opnsense": HealthCheckStub(),
            "tofu": HealthCheckStub(),
        }
        dns_resolver = MagicMock(return_value="1.1.1.1")

        service = DoctorService(health_checks=health_checks, dns_resolver=dns_resolver)
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
        assert all(check.calls == 1 for check in health_checks.values())
        dns_resolver.assert_called_once_with("1.1.1.1")

    def test_run_diagnostics_with_failures(self):
        health_checks = {
            "vcenter": HealthCheckStub(PrerequisiteError("vCenter unreachable")),
            "technitium": HealthCheckStub(PrerequisiteError("Technitium down")),
            "opnsense": HealthCheckStub(PrerequisiteError("OPNsense API error")),
            "tofu": HealthCheckStub(PrerequisiteError("Tofu binary missing")),
        }
        dns_resolver = MagicMock(side_effect=socket.error("DNS resolution failed"))

        service = DoctorService(health_checks=health_checks, dns_resolver=dns_resolver)
        results = service.run_diagnostics()

        assert results["vcenter"]["status"] == "fail"
        assert results["vcenter"]["error"] == "vCenter unreachable"
        
        assert results["technitium"]["status"] == "fail"
        assert results["technitium"]["error"] == "Technitium down"
        
        assert results["opnsense"]["status"] == "fail"
        assert results["opnsense"]["error"] == "OPNsense API error"
        
        assert results["tofu"]["status"] == "fail"
        assert results["tofu"]["error"] == "Tofu binary missing"
        
        assert results["dns"]["status"] == "fail"
        assert results["dns"]["error"] == "DNS resolution failed"

    def test_run_diagnostics_generic_exceptions(self):
        health_checks = {
            "vcenter": HealthCheckStub(Exception("vCenter generic error")),
            "technitium": HealthCheckStub(Exception("Technitium generic error")),
            "opnsense": HealthCheckStub(Exception("OPNsense generic error")),
            "tofu": HealthCheckStub(Exception("Tofu generic error")),
        }

        service = DoctorService(health_checks=health_checks, dns_resolver=MagicMock(return_value="1.1.1.1"))
        results = service.run_diagnostics()

        assert results["vcenter"]["error"] == "vCenter generic error"
        assert results["technitium"]["error"] == "Technitium generic error"
        assert results["opnsense"]["error"] == "OPNsense generic error"
        assert results["tofu"]["error"] == "Tofu generic error"

    def test_run_diagnostics_dns_failure(self):
        dns_resolver = MagicMock(side_effect=socket.gaierror("Name or service not known"))

        service = DoctorService(
            health_checks={"vcenter": HealthCheckStub()},
            dns_resolver=dns_resolver,
        )
        results = service.run_diagnostics()

        assert results["dns"]["status"] == "fail"
        assert "Name or service not known" in results["dns"]["error"]

class TestDoctorCLI:
    @patch('homelab_gitops.cli.core_commands.doctor.ReadOnlyProviderFactory')
    def test_doctor_command_success(self, mock_factory):
        mock_instance = mock_factory.return_value.doctor_service.return_value
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

    @patch('homelab_gitops.cli.core_commands.doctor.ReadOnlyProviderFactory')
    def test_doctor_command_exception(self, mock_factory):
        mock_instance = mock_factory.return_value.doctor_service.return_value
        mock_instance.run_diagnostics.side_effect = Exception("Critical failure")

        import typer
        app = typer.Typer()
        app.command(name="doctor")(doctor_command)

        result = runner.invoke(app, [])
        
        assert result.exit_code == 1
        assert "Diagnostics failed: Critical failure" in result.stdout
