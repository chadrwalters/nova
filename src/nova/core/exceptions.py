"""Core exceptions for the Nova package."""


class NovaError(Exception):
    """Base class for all Nova exceptions."""
    pass


class ValidationError(NovaError):
    """Exception raised when validation fails."""
    pass 