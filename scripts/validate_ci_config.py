#!/usr/bin/env python3
"""
CI Configuration Validator

Automated validation to detect common CI configuration mistakes.
Ensures coverage config isn't duplicated, dependencies are declared,
test files exist, and coverage thresholds are consistent.
"""

import re
import sys
from pathlib import Path
from typing import List, Tuple


class CIValidator:
    """Validates CI configuration consistency and completeness."""

    def __init__(self, repo_root: Path = None):
        """Initialize validator with repository root path."""
        self.repo_root = repo_root or Path.cwd()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.successes: List[str] = []

    def check_coverage_config_duplication(self) -> bool:
        """
        Check 1: Ensure coverage config isn't in both pytest.ini and workflow.

        Returns:
            bool: True if no duplication found, False otherwise.
        """
        check_name = "Coverage Config Duplication"
        pytest_ini = self.repo_root / "pytest.ini"
        workflow_files = list((self.repo_root / ".github" / "workflows").glob("*.yml"))

        if not pytest_ini.exists():
            self.warnings.append(f"{check_name}: pytest.ini not found")
            return True

        # Check for coverage config in pytest.ini
        pytest_ini_content = pytest_ini.read_text()
        pytest_has_coverage = (
            "--cov" in pytest_ini_content or "--fail-under" in pytest_ini_content
        )

        # Check for coverage config in workflows
        workflow_has_coverage = False
        for workflow_file in workflow_files:
            content = workflow_file.read_text()
            if "--cov" in content or "--fail-under" in content:
                workflow_has_coverage = True
                break

        if pytest_has_coverage and workflow_has_coverage:
            self.errors.append(
                f"{check_name}: Coverage config found in both pytest.ini and workflows. "
                "Coverage should be configured in workflows only."
            )
            return False

        self.successes.append(f"{check_name}: No duplication detected")
        return True

    def check_dependencies_declared(self) -> bool:
        """
        Check 2: Verify pytest, pytest-cov, pytest-testinfra in requirements.txt.

        Returns:
            bool: True if all required dependencies are declared, False otherwise.
        """
        check_name = "Dependencies Declared"
        requirements_file = self.repo_root / "requirements.txt"

        if not requirements_file.exists():
            self.errors.append(f"{check_name}: requirements.txt not found")
            return False

        content = requirements_file.read_text().lower()
        required_packages = ["pytest", "pytest-cov", "pytest-testinfra"]
        missing_packages = []

        for package in required_packages:
            if package not in content:
                missing_packages.append(package)

        if missing_packages:
            self.errors.append(
                f"{check_name}: Missing required packages: {', '.join(missing_packages)}"
            )
            return False

        self.successes.append(f"{check_name}: All required packages declared")
        return True

    def check_test_file_references(self) -> bool:
        """
        Check 3: Verify test files exist when referenced in workflows.

        Returns:
            bool: True if all referenced test files exist, False otherwise.
        """
        check_name = "Test File References"
        workflow_files = list((self.repo_root / ".github" / "workflows").glob("*.yml"))
        test_dir = self.repo_root / "tests"
        missing_files = []

        # Pattern to match test file references in workflows
        test_pattern = r"tests/[a-z_/]+\.py"

        for workflow_file in workflow_files:
            content = workflow_file.read_text()
            referenced_tests = re.findall(test_pattern, content)

            for test_ref in referenced_tests:
                test_path = self.repo_root / test_ref
                if not test_path.exists():
                    missing_files.append((workflow_file.name, test_ref))

        if missing_files:
            missing_str = "; ".join(
                [f"{wf}: {test}" for wf, test in missing_files]
            )
            self.errors.append(
                f"{check_name}: Referenced test files do not exist: {missing_str}"
            )
            return False

        self.successes.append(f"{check_name}: All test file references valid")
        return True

    def check_coverage_threshold_consistency(self) -> bool:
        """
        Check 4: Ensure coverage threshold value matches message.

        Extracts --fail-under value and verifies it matches the message/comment.

        Returns:
            bool: True if thresholds are consistent, False otherwise.
        """
        check_name = "Coverage Threshold Consistency"
        workflow_files = list((self.repo_root / ".github" / "workflows").glob("*.yml"))
        inconsistencies = []

        # Pattern to extract fail-under value and surrounding context
        threshold_pattern = r"--fail-under=(\d+)"
        # Look for numbers near threshold/minimum keywords (before or after)
        message_pattern = r"(?:threshold|minimum)[:\s]+([\d]+)|(?:[\d]+)[:\s]*(?:threshold|minimum)"

        for workflow_file in workflow_files:
            content = workflow_file.read_text()
            thresholds = re.findall(threshold_pattern, content)

            if not thresholds:
                continue

            # Get all threshold values
            for threshold_value in thresholds:
                # Search entire file for messages with different values
                matches = re.findall(message_pattern, content)
                # Filter out empty strings from groups
                messages = [m for m in matches if isinstance(m, str) and m]

                for msg_value in messages:
                    if msg_value != threshold_value:
                        inconsistencies.append(
                            f"{workflow_file.name}: "
                            f"Threshold {threshold_value}% but message shows {msg_value}%"
                        )

        if inconsistencies:
            self.errors.append(
                f"{check_name}: {'; '.join(inconsistencies)}"
            )
            return False

        self.successes.append(f"{check_name}: All thresholds consistent")
        return True

    def validate_all(self) -> bool:
        """
        Run all validation checks.

        Returns:
            bool: True if all checks pass, False if any errors found.
        """
        self.check_coverage_config_duplication()
        self.check_dependencies_declared()
        self.check_test_file_references()
        self.check_coverage_threshold_consistency()

        return len(self.errors) == 0

    def report(self) -> int:
        """
        Print validation results.

        Returns:
            int: 0 if all checks pass, 1 if errors found.
        """
        print("\n" + "=" * 70)
        print("CI Configuration Validation Report")
        print("=" * 70 + "\n")

        if self.successes:
            print("Successes:")
            for success in self.successes:
                print(f"  ✅ {success}")
            print()

        if self.warnings:
            print("Warnings:")
            for warning in self.warnings:
                print(f"  ⚠️  {warning}")
            print()

        if self.errors:
            print("Errors:")
            for error in self.errors:
                print(f"  ❌ {error}")
            print()
            print("=" * 70)
            print("Validation FAILED - Please fix the errors above")
            print("=" * 70 + "\n")
            return 1

        print("=" * 70)
        print("Validation PASSED - All checks successful")
        print("=" * 70 + "\n")
        return 0


def main():
    """Run the CI configuration validator."""
    validator = CIValidator()
    validator.validate_all()
    exit_code = validator.report()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
