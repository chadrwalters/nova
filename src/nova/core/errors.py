"""Error models for the pipeline."""

from typing import Optional, List, Dict, Any


class NovaError(Exception):
    """Base class for all Nova errors."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class ValidationError(NovaError):
    """Error raised when validation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize validation error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class ProcessingError(NovaError):
    """Error raised when processing fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize processing error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class ConfigurationError(NovaError):
    """Error raised when configuration is invalid."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize configuration error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class ResourceError(NovaError):
    """Error raised when resource access fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize resource error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class HandlerError(NovaError):
    """Error raised when handler fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize handler error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class ComponentError(NovaError):
    """Error raised when component fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize component error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class FileOperationError(NovaError):
    """Error raised when file operation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize file operation error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class PipelineError(NovaError):
    """Error raised when pipeline fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize pipeline error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class PhaseError(NovaError):
    """Error raised when phase fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize phase error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class CacheError(NovaError):
    """Error raised when cache operation fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize cache error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class MonitoringError(NovaError):
    """Error raised when monitoring fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize monitoring error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class MetricsError(NovaError):
    """Error raised when metrics collection fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize metrics error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class TimingError(NovaError):
    """Error raised when timing fails."""

    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        """Initialize timing error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message, details)


class ErrorContext:
    """Context information for errors."""

    def __init__(self, source: str, details: Optional[Dict[str, Any]] = None, errors: Optional[List[NovaError]] = None):
        """Initialize error context.
        
        Args:
            source: Source of the error (e.g. component name, phase name)
            details: Optional context details
            errors: Optional list of related errors
        """
        self.source = source
        self.details = details or {}
        self.errors = errors or []

    def add_error(self, error: NovaError) -> None:
        """Add error to context.
        
        Args:
            error: Error to add
        """
        self.errors.append(error)

    def add_detail(self, key: str, value: Any) -> None:
        """Add detail to context.
        
        Args:
            key: Detail key
            value: Detail value
        """
        self.details[key] = value

    def get_errors(self) -> List[NovaError]:
        """Get list of errors.
        
        Returns:
            List of errors
        """
        return self.errors

    def get_details(self) -> Dict[str, Any]:
        """Get context details.
        
        Returns:
            Context details
        """
        return self.details

    def get_source(self) -> str:
        """Get error source.
        
        Returns:
            Error source
        """
        return self.source 