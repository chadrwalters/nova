"""Error handling for Nova document processing."""
from typing import Dict, Optional


class NovaError(Exception):
    """Base exception for Nova errors."""
    
    def __init__(
        self,
        message: str,
        context: Optional[Dict] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        """Initialize error.
        
        Args:
            message: Error message.
            context: Optional context dictionary.
            original_error: Optional original exception.
        """
        super().__init__(message)
        self.message = message
        self.context = context or {}
        self.original_error = original_error


class ConfigurationError(NovaError):
    """Error in configuration."""
    pass


class HandlerError(NovaError):
    """Error in document handler."""
    pass


class PhaseError(NovaError):
    """Error in processing phase."""
    pass


class ValidationError(NovaError):
    """Error in data validation."""
    pass


class ResourceError(NovaError):
    """Error accessing resources."""
    pass


class ProcessingError(NovaError):
    """Error during document processing."""
    pass


def wrap_error(
    error: Exception,
    message: str,
    context: Optional[Dict] = None,
) -> NovaError:
    """Wrap an exception in a Nova error.
    
    Args:
        error: Original exception.
        message: Error message.
        context: Optional context dictionary.
    
    Returns:
        Wrapped Nova error.
    """
    if isinstance(error, NovaError):
        if context:
            error.context.update(context)
        return error
    
    return ProcessingError(
        message=message,
        context=context,
        original_error=error,
    ) 