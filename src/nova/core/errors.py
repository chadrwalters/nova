"""Pipeline error classes."""

from typing import Optional, Dict, Any


class PipelineError(Exception):
    """Base class for pipeline errors."""
    
    def __init__(self, message: str, phase: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None):
        """Initialize pipeline error.
        
        Args:
            message: Error message
            phase: Optional phase name where error occurred
            metadata: Optional error metadata
        """
        super().__init__(message)
        self.phase = phase
        self.metadata = metadata or {}


class ValidationError(PipelineError):
    """Validation error."""
    pass


class ConfigurationError(PipelineError):
    """Configuration error."""
    pass


class ProcessingError(PipelineError):
    """Processing error."""
    pass


class DependencyError(PipelineError):
    """Dependency error."""
    pass


class ResourceError(PipelineError):
    """Resource error."""
    pass


class StateError(PipelineError):
    """State error."""
    pass


class HandlerError(PipelineError):
    """Handler error."""
    pass


class ErrorContext:
    """Context for error handling."""
    
    def __init__(self, phase: Optional[str] = None, handler: Optional[str] = None):
        """Initialize error context.
        
        Args:
            phase: Optional phase name
            handler: Optional handler name
        """
        self.phase = phase
        self.handler = handler
        self.metadata: Dict[str, Any] = {}
        
    def add_metadata(self, key: str, value: Any) -> None:
        """Add metadata to error context.
        
        Args:
            key: Metadata key
            value: Metadata value
        """
        self.metadata[key] = value
        
    def get_metadata(self) -> Dict[str, Any]:
        """Get error context metadata.
        
        Returns:
            Metadata dictionary
        """
        return self.metadata.copy() 