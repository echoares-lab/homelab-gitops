"""Unit tests for manage.py CLI wrapper.

Tests CLI command mapping to services using Typer's CliRunner.
Focus on command invocation, help text, aliases, and error handling.
"""

import pytest
from typer.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock
from manage import app

runner = CliRunner()


class TestBuildCommand:
    """Test build command."""

    @pytest.mark.unit
    def test_build_command_help(self):
        """Test build command has help."""
        result = runner.invoke(app, ["build", "--help"])
        assert result.exit_code == 0
        assert "Build golden image" in result.output

    @pytest.mark.unit
    def test_build_command_default_target(self):
        """Test build command with default target."""
        with patch("manage._orchestrate.build") as mock_build:
            mock_build.return_value = True
            result = runner.invoke(app, ["build"])
            assert result.exit_code == 0
            mock_build.assert_called_once_with("photon-docker")

    @pytest.mark.unit
    def test_build_command_custom_target(self):
        """Test build command with custom target."""
        with patch("manage._orchestrate.build") as mock_build:
            mock_build.return_value = True
            result = runner.invoke(app, ["build", "ubuntu-2404"])
            assert result.exit_code == 0
            mock_build.assert_called_once_with("ubuntu-2404")

    @pytest.mark.unit
    def test_build_command_failure(self):
        """Test build command handles service failure."""
        with patch("manage._orchestrate.build") as mock_build:
            mock_build.return_value = False
            result = runner.invoke(app, ["build"])
            assert result.exit_code == 1

    @pytest.mark.unit
    def test_build_alias_bu(self):
        """Test 'bu' alias for build."""
        with patch("manage._orchestrate.build") as mock_build:
            mock_build.return_value = True
            result = runner.invoke(app, ["bu"])
            assert result.exit_code == 0
            mock_build.assert_called_once()


class TestLintCommand:
    """Test lint command."""

    @pytest.mark.unit
    def test_lint_command_help(self):
        """Test lint command has help."""
        result = runner.invoke(app, ["lint", "--help"])
        assert result.exit_code == 0
        assert "Validate profile" in result.output

    @pytest.mark.unit
    def test_lint_command_defaults(self):
        """Test lint command with default arguments."""
        with patch("manage._orchestrate.lint") as mock_lint:
            mock_lint.return_value = True
            result = runner.invoke(app, ["lint"])
            assert result.exit_code == 0
            mock_lint.assert_called_once_with("photon-docker", "01")

    @pytest.mark.unit
    def test_lint_command_custom_profile(self):
        """Test lint command with custom profile."""
        with patch("manage._orchestrate.lint") as mock_lint:
            mock_lint.return_value = True
            result = runner.invoke(app, ["lint", "ubuntu-2404-base"])
            assert result.exit_code == 0
            mock_lint.assert_called_once_with("ubuntu-2404-base", "01")

    @pytest.mark.unit
    def test_lint_command_custom_profile_and_index(self):
        """Test lint command with custom profile and index."""
        with patch("manage._orchestrate.lint") as mock_lint:
            mock_lint.return_value = True
            result = runner.invoke(app, ["lint", "ubuntu-2404-base", "02"])
            assert result.exit_code == 0
            mock_lint.assert_called_once_with("ubuntu-2404-base", "02")

    @pytest.mark.unit
    def test_lint_command_failure(self):
        """Test lint command handles service failure."""
        with patch("manage._orchestrate.lint") as mock_lint:
            mock_lint.return_value = False
            result = runner.invoke(app, ["lint", "bad-profile"])
            assert result.exit_code == 1

    @pytest.mark.unit
    def test_lint_alias_li(self):
        """Test 'li' alias for lint."""
        with patch("manage._orchestrate.lint") as mock_lint:
            mock_lint.return_value = True
            result = runner.invoke(app, ["li"])
            assert result.exit_code == 0
            mock_lint.assert_called_once()


class TestDeployCommand:
    """Test deploy command."""

    @pytest.mark.unit
    def test_deploy_command_help(self):
        """Test deploy command has help."""
        result = runner.invoke(app, ["deploy", "--help"])
        assert result.exit_code == 0
        assert "Provision VM" in result.output

    @pytest.mark.unit
    def test_deploy_command_defaults(self):
        """Test deploy command with defaults."""
        with patch("manage._orchestrate.deploy") as mock_deploy:
            mock_deploy.return_value = True
            result = runner.invoke(app, ["deploy"])
            assert result.exit_code == 0
            mock_deploy.assert_called_once_with(
                "photon-docker",
                "01",
                host="esxi-01.mgmt.plexplease.com",
                mac=None
            )

    @pytest.mark.unit
    def test_deploy_command_custom_host(self):
        """Test deploy command with custom host."""
        with patch("manage._orchestrate.deploy") as mock_deploy:
            mock_deploy.return_value = True
            result = runner.invoke(app, ["deploy", "--host", "esxi-02.mgmt.plexplease.com"])
            assert result.exit_code == 0
            mock_deploy.assert_called_once_with(
                "photon-docker",
                "01",
                host="esxi-02.mgmt.plexplease.com",
                mac=None
            )

    @pytest.mark.unit
    def test_deploy_command_custom_mac(self):
        """Test deploy command with MAC address."""
        with patch("manage._orchestrate.deploy") as mock_deploy:
            mock_deploy.return_value = True
            result = runner.invoke(app, ["deploy", "--mac", "00:50:56:aa:bb:cc"])
            assert result.exit_code == 0
            mock_deploy.assert_called_once_with(
                "photon-docker",
                "01",
                host="esxi-01.mgmt.plexplease.com",
                mac="00:50:56:aa:bb:cc"
            )

    @pytest.mark.unit
    def test_deploy_command_all_options(self):
        """Test deploy command with all options."""
        with patch("manage._orchestrate.deploy") as mock_deploy:
            mock_deploy.return_value = True
            result = runner.invoke(app, [
                "deploy",
                "ubuntu-2404-base",
                "03",
                "--host", "esxi-03.mgmt.plexplease.com",
                "--mac", "00:50:56:cc:dd:ee"
            ])
            assert result.exit_code == 0
            mock_deploy.assert_called_once_with(
                "ubuntu-2404-base",
                "03",
                host="esxi-03.mgmt.plexplease.com",
                mac="00:50:56:cc:dd:ee"
            )

    @pytest.mark.unit
    def test_deploy_alias_dep(self):
        """Test 'dep' alias for deploy."""
        with patch("manage._orchestrate.deploy") as mock_deploy:
            mock_deploy.return_value = True
            result = runner.invoke(app, ["dep"])
            assert result.exit_code == 0
            mock_deploy.assert_called_once()


class TestConfigCommand:
    """Test config command."""

    @pytest.mark.unit
    def test_config_command_help(self):
        """Test config command has help."""
        result = runner.invoke(app, ["config", "--help"])
        assert result.exit_code == 0
        assert "Apply Ansible configuration" in result.output

    @pytest.mark.unit
    def test_config_command_defaults(self):
        """Test config command with defaults."""
        with patch("manage._orchestrate.config") as mock_config:
            mock_config.return_value = True
            result = runner.invoke(app, ["config"])
            assert result.exit_code == 0
            mock_config.assert_called_once_with("photon-docker", "01")

    @pytest.mark.unit
    def test_config_command_custom_profile(self):
        """Test config command with custom profile."""
        with patch("manage._orchestrate.config") as mock_config:
            mock_config.return_value = True
            result = runner.invoke(app, ["config", "ubuntu-2404-base"])
            assert result.exit_code == 0
            mock_config.assert_called_once_with("ubuntu-2404-base", "01")

    @pytest.mark.unit
    def test_config_command_custom_profile_and_index(self):
        """Test config command with profile and index."""
        with patch("manage._orchestrate.config") as mock_config:
            mock_config.return_value = True
            result = runner.invoke(app, ["config", "ubuntu-2404-base", "02"])
            assert result.exit_code == 0
            mock_config.assert_called_once_with("ubuntu-2404-base", "02")

    @pytest.mark.unit
    def test_config_alias_cfg(self):
        """Test 'cfg' alias for config."""
        with patch("manage._orchestrate.config") as mock_config:
            mock_config.return_value = True
            result = runner.invoke(app, ["cfg"])
            assert result.exit_code == 0
            mock_config.assert_called_once()


class TestTestCommand:
    """Test test command."""

    @pytest.mark.unit
    def test_test_command_help(self):
        """Test test command has help."""
        result = runner.invoke(app, ["test", "--help"])
        assert result.exit_code == 0
        assert "Run testinfra validation" in result.output

    @pytest.mark.unit
    def test_test_command_defaults(self):
        """Test test command with defaults."""
        with patch("manage._orchestrate.test") as mock_test:
            mock_test.return_value = True
            result = runner.invoke(app, ["test"])
            assert result.exit_code == 0
            mock_test.assert_called_once_with("photon-docker", "01")

    @pytest.mark.unit
    def test_test_command_custom_profile(self):
        """Test test command with custom profile."""
        with patch("manage._orchestrate.test") as mock_test:
            mock_test.return_value = True
            result = runner.invoke(app, ["test", "ubuntu-2404-base"])
            assert result.exit_code == 0
            mock_test.assert_called_once_with("ubuntu-2404-base", "01")

    @pytest.mark.unit
    def test_test_alias_ts(self):
        """Test 'ts' alias for test."""
        with patch("manage._orchestrate.test") as mock_test:
            mock_test.return_value = True
            result = runner.invoke(app, ["ts"])
            assert result.exit_code == 0
            mock_test.assert_called_once()


class TestDestroyCommand:
    """Test destroy command."""

    @pytest.mark.unit
    def test_destroy_command_help(self):
        """Test destroy command has help."""
        result = runner.invoke(app, ["destroy", "--help"])
        assert result.exit_code == 0
        assert "Destroy VM" in result.output

    @pytest.mark.unit
    def test_destroy_command_requires_identifier(self):
        """Test destroy command requires identifier argument."""
        result = runner.invoke(app, ["destroy"])
        assert result.exit_code != 0
        assert "Missing argument" in result.output

    @pytest.mark.unit
    def test_destroy_command_aborted(self):
        """Test destroy command can be aborted."""
        with patch("manage._orchestrate.destroy") as mock_destroy:
            result = runner.invoke(app, ["destroy", "test-vm"], input="n\n")
            assert result.exit_code == 0
            mock_destroy.assert_not_called()

    @pytest.mark.unit
    def test_destroy_command_by_name(self):
        """Test destroy command with VM name."""
        with patch("manage._orchestrate.destroy") as mock_destroy:
            mock_destroy.return_value = True
            result = runner.invoke(app, ["destroy", "test-vm"], input="y\n")
            assert result.exit_code == 0
            mock_destroy.assert_called_once_with("test-vm")

    @pytest.mark.unit
    def test_destroy_command_by_ip(self):
        """Test destroy command with VM IP."""
        with patch("manage._orchestrate.destroy") as mock_destroy:
            mock_destroy.return_value = True
            result = runner.invoke(app, ["destroy", "10.10.10.50"], input="y\n")
            assert result.exit_code == 0
            mock_destroy.assert_called_once_with("10.10.10.50")

    @pytest.mark.unit
    def test_destroy_command_by_mac(self):
        """Test destroy command with MAC address."""
        with patch("manage._orchestrate.destroy") as mock_destroy:
            mock_destroy.return_value = True
            result = runner.invoke(app, ["destroy", "00:50:56:aa:bb:cc"], input="y\n")
            assert result.exit_code == 0
            mock_destroy.assert_called_once_with("00:50:56:aa:bb:cc")

    @pytest.mark.unit
    def test_destroy_alias_rm(self):
        """Test 'rm' alias for destroy."""
        with patch("manage._orchestrate.destroy") as mock_destroy:
            mock_destroy.return_value = True
            result = runner.invoke(app, ["rm", "test-vm"], input="y\n")
            assert result.exit_code == 0
            mock_destroy.assert_called_once()


class TestStatusCommand:
    """Test status command."""

    @pytest.mark.unit
    def test_status_command_help(self):
        """Test status command has help."""
        result = runner.invoke(app, ["status", "--help"])
        assert result.exit_code == 0
        assert "fleet health" in result.output.lower()

    @pytest.mark.unit
    def test_status_command_no_vms(self):
        """Test status command with no VMs."""
        with patch("manage._orchestrate.status") as mock_status:
            mock_status.return_value = []
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "No VMs found" in result.output

    @pytest.mark.unit
    def test_status_command_with_vms(self):
        """Test status command with VMs."""
        with patch("manage._orchestrate.status") as mock_status:
            mock_status.return_value = [
                {
                    "name": "test-vm-01",
                    "power": "on",
                    "ip": "10.10.10.50",
                    "tags": ["docker", "primary_dns"]
                }
            ]
            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "test-vm-01" in result.output
            assert "10.10.10.50" in result.output

    @pytest.mark.unit
    def test_status_alias_st(self):
        """Test 'st' alias for status."""
        with patch("manage._orchestrate.status") as mock_status:
            mock_status.return_value = []
            result = runner.invoke(app, ["st"])
            assert result.exit_code == 0
            mock_status.assert_called_once()


class TestAllCommand:
    """Test all (complete pipeline) command."""

    @pytest.mark.unit
    def test_all_command_help(self):
        """Test all command has help."""
        result = runner.invoke(app, ["all", "--help"])
        assert result.exit_code == 0
        assert "complete pipeline" in result.output.lower()

    @pytest.mark.unit
    def test_all_command_defaults(self):
        """Test all command with defaults."""
        with patch("manage._orchestrate.all") as mock_all:
            mock_all.return_value = True
            result = runner.invoke(app, ["all"])
            assert result.exit_code == 0
            mock_all.assert_called_once_with(
                "photon-docker",
                "01",
                "esxi-01.mgmt.plexplease.com"
            )

    @pytest.mark.unit
    def test_all_command_custom_profile(self):
        """Test all command with custom profile."""
        with patch("manage._orchestrate.all") as mock_all:
            mock_all.return_value = True
            result = runner.invoke(app, ["all", "ubuntu-2404-base"])
            assert result.exit_code == 0
            mock_all.assert_called_once_with(
                "ubuntu-2404-base",
                "01",
                "esxi-01.mgmt.plexplease.com"
            )

    @pytest.mark.unit
    def test_all_command_custom_host(self):
        """Test all command with custom host."""
        with patch("manage._orchestrate.all") as mock_all:
            mock_all.return_value = True
            result = runner.invoke(app, ["all", "--host", "esxi-02.mgmt.plexplease.com"])
            assert result.exit_code == 0
            mock_all.assert_called_once_with(
                "photon-docker",
                "01",
                "esxi-02.mgmt.plexplease.com"
            )

    @pytest.mark.unit
    def test_all_command_all_options(self):
        """Test all command with all options."""
        with patch("manage._orchestrate.all") as mock_all:
            mock_all.return_value = True
            result = runner.invoke(app, [
                "all",
                "ubuntu-2404-base",
                "03",
                "--host", "esxi-03.mgmt.plexplease.com"
            ])
            assert result.exit_code == 0
            mock_all.assert_called_once_with(
                "ubuntu-2404-base",
                "03",
                "esxi-03.mgmt.plexplease.com"
            )

    @pytest.mark.unit
    def test_all_alias_a(self):
        """Test 'a' alias for all."""
        with patch("manage._orchestrate.all") as mock_all:
            mock_all.return_value = True
            result = runner.invoke(app, ["a"])
            assert result.exit_code == 0
            mock_all.assert_called_once()


class TestCreateProfileCommand:
    """Test create-profile command."""

    @pytest.mark.unit
    def test_create_profile_command_help(self):
        """Test create-profile command has help."""
        result = runner.invoke(app, ["create-profile", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_create_profile_command_interactive(self):
        """Test create-profile command interactively."""
        with patch("manage._config.create_profile") as mock_create:
            mock_create.return_value = True
            result = runner.invoke(app, ["create-profile"], input="test-profile\n2\n4\n50\ndocker,primary_dns\n")
            assert result.exit_code == 0
            assert "Created profile" in result.output

    @pytest.mark.unit
    def test_create_profile_command_duplicate_error(self):
        """Test create-profile command handles duplicate error."""
        with patch("manage._config.create_profile") as mock_create:
            mock_create.side_effect = FileExistsError("Profile already exists")
            result = runner.invoke(app, ["create-profile"], input="test-profile\n2\n4\n50\ndocker\n")
            assert result.exit_code == 1
            assert "Error" in result.output


class TestCreateRoleCommand:
    """Test create-role command."""

    @pytest.mark.unit
    def test_create_role_command_help(self):
        """Test create-role command has help."""
        result = runner.invoke(app, ["create-role", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_create_role_command_interactive(self):
        """Test create-role command interactively."""
        with patch("manage._config.create_role") as mock_create:
            mock_create.return_value = True
            result = runner.invoke(app, ["create-role"], input="harden_os\n")
            assert result.exit_code == 0
            assert "Created role" in result.output

    @pytest.mark.unit
    def test_create_role_command_duplicate_error(self):
        """Test create-role command handles duplicate error."""
        with patch("manage._config.create_role") as mock_create:
            mock_create.side_effect = FileExistsError("Role already exists")
            result = runner.invoke(app, ["create-role"], input="harden_os\n")
            assert result.exit_code == 1
            assert "Error" in result.output


class TestDNSCommands:
    """Test DNS commands."""

    @pytest.mark.unit
    def test_dns_list_command_help(self):
        """Test dns-list command has help."""
        result = runner.invoke(app, ["dns-list", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_dns_list_command_no_records(self):
        """Test dns-list command with no records."""
        with patch("manage._dns.list_records") as mock_list:
            mock_list.return_value = []
            result = runner.invoke(app, ["dns-list"])
            assert result.exit_code == 0
            assert "No DNS records found" in result.output

    @pytest.mark.unit
    def test_dns_list_command_with_records(self):
        """Test dns-list command with records."""
        with patch("manage._dns.list_records") as mock_list:
            mock_list.return_value = [
                {
                    "name": "test.example.com",
                    "type": "A",
                    "value": "10.10.10.50",
                    "ttl": 3600
                }
            ]
            result = runner.invoke(app, ["dns-list"])
            assert result.exit_code == 0
            assert "test.example.com" in result.output

    @pytest.mark.unit
    def test_dns_create_command_help(self):
        """Test dns-create command has help."""
        result = runner.invoke(app, ["dns-create", "--help"])
        assert result.exit_code == 0

    @pytest.mark.unit
    def test_dns_create_command(self):
        """Test dns-create command."""
        with patch("manage._dns.create_record") as mock_create:
            mock_create.return_value = True
            result = runner.invoke(app, ["dns-create", "test.example.com", "10.10.10.50"])
            assert result.exit_code == 0
            assert "Created DNS record" in result.output
            mock_create.assert_called_once_with("test.example.com", "10.10.10.50")
