"""Pipeline error classes."""


class PipelineError(Exception):
    """Base class for pipeline errors."""
    pass


class ValidationError(PipelineError):
    """Raised when validation fails."""
    pass


class ProcessingError(PipelineError):
    """Raised when processing fails."""
    pass


class ConfigurationError(PipelineError):
    """Raised when configuration is invalid."""
    pass


class DependencyError(PipelineError):
    """Raised when dependencies are invalid."""
    pass 