"""
Unit tests for CI Configuration Validator.

Tests the CIValidator class to ensure all CI configuration checks work correctly.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from scripts.validate_ci_config import CIValidator


class TestCIValidator:
    """Test suite for CIValidator class."""

    def test_validator_initializes(self):
        """Test that CIValidator initializes correctly."""
        validator = CIValidator()
        assert validator.repo_root is not None
        assert isinstance(validator.repo_root, Path)
        assert isinstance(validator.errors, list)
        assert isinstance(validator.warnings, list)
        assert isinstance(validator.successes, list)
        assert len(validator.errors) == 0
        assert len(validator.warnings) == 0
        assert len(validator.successes) == 0

    def test_coverage_config_duplication_check(self):
        """Test coverage configuration duplication detection."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)

            # Create pytest.ini without coverage config
            pytest_ini = repo_root / "pytest.ini"
            pytest_ini.write_text("[pytest]\ntestpaths = tests\n")

            # Create workflow without coverage config
            workflow = repo_root / ".github" / "workflows" / "test.yml"
            workflow.write_text("name: Test\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

            validator = CIValidator(repo_root)
            result = validator.check_coverage_config_duplication()
            assert result is True
            assert any("No duplication detected" in s for s in validator.successes)

    def test_coverage_config_duplication_check_with_duplication(self):
        """Test coverage duplication detection when both files have config."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)

            # Create pytest.ini with coverage config
            pytest_ini = repo_root / "pytest.ini"
            pytest_ini.write_text(
                "[pytest]\n"
                "testpaths = tests\n"
                "addopts = --cov=mymodule --fail-under=80\n"
            )

            # Create workflow with coverage config
            workflow = repo_root / ".github" / "workflows" / "test.yml"
            workflow.write_text(
                "name: Test\njobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: pytest --cov=mymodule --fail-under=80\n"
            )

            validator = CIValidator(repo_root)
            result = validator.check_coverage_config_duplication()
            assert result is False
            assert any("found in both" in e for e in validator.errors)

    def test_coverage_report_format_in_workflow_is_not_duplication(self):
        """A workflow may add --cov-report formats on top of the pytest.ini gate.

        Since E1.T4 the gate (--cov=<target>, --cov-fail-under) lives in
        pytest.ini addopts only; CI adds json/html reports. Comment lines that
        mention the flags are documentation, not configuration.
        """
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)

            (repo_root / "pytest.ini").write_text(
                "[pytest]\n"
                "addopts =\n"
                "    --cov=mymodule\n"
                "    --cov-fail-under=85\n"
            )
            (repo_root / ".github" / "workflows" / "test.yml").write_text(
                "name: Test\njobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      #   --cov-fail-under=85 lives in pytest.ini\n"
                "      - run: pytest --cov-report=json --cov-report=html:htmlcov\n"
            )

            validator = CIValidator(repo_root)
            assert validator.check_coverage_config_duplication() is True
            assert not validator.errors

    def test_dependencies_declared_check(self):
        """Test that dependencies are correctly declared."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Create requirements.txt with all required packages
            requirements = repo_root / "requirements.txt"
            requirements.write_text(
                "pytest\n"
                "pytest-cov\n"
                "pytest-testinfra\n"
                "other-package\n"
            )

            validator = CIValidator(repo_root)
            result = validator.check_dependencies_declared()
            assert result is True
            assert any("All required packages declared" in s for s in validator.successes)

    def test_dependencies_declared_check_missing(self):
        """Test that missing dependencies are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)

            # Create requirements.txt missing pytest-cov
            requirements = repo_root / "requirements.txt"
            requirements.write_text(
                "pytest\n"
                "pytest-testinfra\n"
                "other-package\n"
            )

            validator = CIValidator(repo_root)
            result = validator.check_dependencies_declared()
            assert result is False
            assert any("pytest-cov" in e for e in validator.errors)

    def test_test_file_references_check(self):
        """Test that referenced test files are verified to exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)
            (repo_root / "tests").mkdir(parents=True)

            # Create actual test files
            test_file = repo_root / "tests" / "test_example.py"
            test_file.write_text("# test\n")

            # Create workflow referencing existing test file
            workflow = repo_root / ".github" / "workflows" / "test.yml"
            workflow.write_text(
                "name: Test\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: pytest tests/test_example.py\n"
            )

            validator = CIValidator(repo_root)
            result = validator.check_test_file_references()
            assert result is True
            assert any("All test file references valid" in s for s in validator.successes)

    def test_test_file_references_check_missing(self):
        """Test that missing test files are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)
            (repo_root / "tests").mkdir(parents=True)

            # Create workflow referencing non-existent test file
            workflow = repo_root / ".github" / "workflows" / "test.yml"
            workflow.write_text(
                "name: Test\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - run: pytest tests/test_nonexistent.py\n"
            )

            validator = CIValidator(repo_root)
            result = validator.check_test_file_references()
            assert result is False
            assert any("do not exist" in e for e in validator.errors)

    def test_coverage_threshold_consistency_check(self):
        """Test that coverage thresholds are consistent."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)

            # Create workflow with consistent threshold
            workflow = repo_root / ".github" / "workflows" / "test.yml"
            workflow.write_text(
                "name: Test\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - name: Check coverage\n"
                "        run: pytest --fail-under=85\n"
                "      - name: Report\n"
                "        run: echo 'Coverage minimum: 85%'\n"
            )

            validator = CIValidator(repo_root)
            result = validator.check_coverage_threshold_consistency()
            assert result is True
            assert any("consistent" in s for s in validator.successes)

    def test_coverage_threshold_consistency_check_inconsistent(self):
        """Test that inconsistent thresholds are detected."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)

            # Create workflow with inconsistent thresholds
            workflow = repo_root / ".github" / "workflows" / "test.yml"
            workflow.write_text(
                "name: Test\n"
                "jobs:\n"
                "  test:\n"
                "    runs-on: ubuntu-latest\n"
                "    steps:\n"
                "      - name: Check coverage\n"
                "        run: pytest --fail-under=85\n"
                "      - name: Report\n"
                "        run: echo 'Coverage minimum: 90%'\n"
            )

            validator = CIValidator(repo_root)
            result = validator.check_coverage_threshold_consistency()
            assert result is False
            assert any("Threshold" in e and "message shows" in e for e in validator.errors)

    def test_validate_all_runs_all_checks(self):
        """Test that validate_all() runs all checks."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)
            (repo_root / "tests").mkdir(parents=True)

            # Set up valid configuration
            pytest_ini = repo_root / "pytest.ini"
            pytest_ini.write_text("[pytest]\ntestpaths = tests\n")

            requirements = repo_root / "requirements.txt"
            requirements.write_text(
                "pytest\npytest-cov\npytest-testinfra\n"
            )

            test_file = repo_root / "tests" / "test_example.py"
            test_file.write_text("# test\n")

            workflow = repo_root / ".github" / "workflows" / "test.yml"
            workflow.write_text(
                "name: Test\njobs:\n  test:\n    runs-on: ubuntu-latest\n"
            )

            validator = CIValidator(repo_root)
            result = validator.validate_all()
            assert result is True
            # Should have 4 successes (one for each check)
            assert len(validator.successes) >= 4

    def test_report_output(self):
        """Test that report() generates correct output."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)

            pytest_ini = repo_root / "pytest.ini"
            pytest_ini.write_text("[pytest]\ntestpaths = tests\n")

            requirements = repo_root / "requirements.txt"
            requirements.write_text("pytest\npytest-cov\npytest-testinfra\n")

            workflow = repo_root / ".github" / "workflows" / "test.yml"
            workflow.write_text("name: Test\njobs:\n  test:\n    runs-on: ubuntu-latest\n")

            validator = CIValidator(repo_root)
            validator.validate_all()

            # Capture report output
            with patch("builtins.print") as mock_print:
                exit_code = validator.report()
                assert exit_code == 0
                # Verify print was called (report generated output)
                assert mock_print.call_count > 0

    def test_report_with_errors(self):
        """Test that report() returns error code when validation fails."""
        with tempfile.TemporaryDirectory() as tmpdir:
            repo_root = Path(tmpdir)
            (repo_root / ".github" / "workflows").mkdir(parents=True)

            requirements = repo_root / "requirements.txt"
            requirements.write_text("other-package\n")  # Missing pytest

            validator = CIValidator(repo_root)
            validator.validate_all()

            with patch("builtins.print") as mock_print:
                exit_code = validator.report()
                assert exit_code == 1
                # Verify error output was printed
                assert mock_print.call_count > 0
