"""Driver layer exceptions."""


class DriverError(Exception):
    """Base exception for driver layer."""
    pass


class PrerequisiteError(DriverError):
    """Required tool or credential not available."""
    pass


class ExecutionError(DriverError):
    """Driver execution failed."""
    pass


class TimeoutError(DriverError):
    """Execution timed out."""
    pass
