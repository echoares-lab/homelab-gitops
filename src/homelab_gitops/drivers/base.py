"""Abstract base class for infrastructure drivers."""

from abc import ABC, abstractmethod
from homelab_gitops.domain.models import Task, TaskResult


class Driver(ABC):
    """Abstract base for all infrastructure drivers."""

    @abstractmethod
    def execute(self, task: Task) -> TaskResult:
        """Execute a task and return result.

        Args:
            task: Task to execute (contains profile, type, target)

        Returns:
            TaskResult with success/failure, output, duration

        Raises:
            DriverError: Execution failed (subclass for specific errors)
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """Validate prerequisites are met.

        Returns:
            True if driver is ready to execute

        Raises:
            PrerequisiteError: Required tool or credential not available
        """
        pass
