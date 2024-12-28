"""Pipeline error classes."""


class PipelineError(Exception):
    """Base class for pipeline errors."""
    pass


class ValidationError(PipelineError):
    """Error raised when validation fails."""
    pass


class ProcessingError(PipelineError):
    """Error raised when processing fails."""
    pass


class ConfigurationError(PipelineError):
    """Error raised when configuration is invalid."""
    pass


class DependencyError(PipelineError):
    """Error raised when a dependency is missing or invalid."""
    pass 