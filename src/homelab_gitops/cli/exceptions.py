"""CLI-specific exceptions."""


class CLIError(Exception):
    """Base CLI exception."""
    pass


class CommandError(CLIError):
    """Command execution failed."""
    pass


class ArgumentError(CLIError):
    """Invalid command arguments."""
    pass
