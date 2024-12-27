"""Core error classes and utilities."""

from typing import Optional, Dict, Any


class NovaError(Exception):
    """Base class for all Nova exceptions."""
    
    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize error.
        
        Args:
            message: Error message
            details: Optional error details
        """
        super().__init__(message)
        self.message = message
        self.details = details or {}


class PipelineError(NovaError):
    """Error raised during pipeline execution."""
    
    def __init__(
        self,
        message: str,
        phase: Optional[str] = None,
        step: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize pipeline error.
        
        Args:
            message: Error message
            phase: Optional pipeline phase
            step: Optional pipeline step
            details: Optional error details
        """
        super().__init__(message, details)
        self.phase = phase
        self.step = step


class ProcessorError(PipelineError):
    """Error raised by processors."""
    pass


class HandlerError(PipelineError):
    """Error raised by handlers."""
    pass


class ConfigurationError(NovaError):
    """Error raised for configuration issues."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Optional configuration key that caused the error
            details: Optional error details
        """
        super().__init__(message, details)
        self.config_key = config_key


class StateError(PipelineError):
    """Error raised for invalid state transitions."""
    
    def __init__(
        self,
        message: str,
        current_state: Optional[str] = None,
        target_state: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize state error.
        
        Args:
            message: Error message
            current_state: Optional current state
            target_state: Optional target state
            details: Optional error details
        """
        super().__init__(message, details)
        self.current_state = current_state
        self.target_state = target_state


class FileError(NovaError):
    """Error raised for file operations."""
    pass


class ValidationError(NovaError):
    """Error raised for validation failures."""
    pass 


class ProcessingError(NovaError):
    """Error raised during file processing."""
    
    def __init__(
        self,
        message: str,
        file_path: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ) -> None:
        """Initialize processing error.
        
        Args:
            message: Error message
            file_path: Optional path to file being processed
            details: Optional error details
        """
        super().__init__(message, details)
        self.file_path = file_path


class ParseError(ProcessingError):
    """Error raised during parsing."""
    pass


class AttachmentError(ProcessingError):
    """Error raised during attachment handling."""
    pass


class AttachmentNotFoundError(AttachmentError):
    """Error raised when an attachment file is not found."""
    pass


class ImageProcessingError(ProcessingError):
    """Error raised during image processing."""
    pass


class OfficeProcessingError(ProcessingError):
    """Error raised during office document processing."""
    pass


class AttachmentProcessingError(ProcessingError):
    """Error raised during attachment processing."""
    pass 