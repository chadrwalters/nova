"""Custom exceptions for Nova document processor."""

class NovaError(Exception):
    """Base class for all Nova errors."""
    pass

class ConfigurationError(NovaError):
    """Raised when there is a configuration error."""
    pass

class ProcessingError(NovaError):
    """Raised when document processing fails."""
    pass

class PipelineError(NovaError):
    """Raised when there is a pipeline error."""
    pass

class HandlerError(NovaError):
    """Raised when a handler encounters an error."""
    pass

class ValidationError(NovaError):
    """Raised when validation fails."""
    pass

class FileError(NovaError):
    """Raised when there is a file operation error."""
    pass

class StateError(NovaError):
    """Raised when there is a state management error."""
    pass

class APIError(NovaError):
    """Raised when there is an API error."""
    pass 