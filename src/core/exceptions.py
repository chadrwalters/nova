"""Custom exceptions for the document processing pipeline."""

from typing import Optional, Dict, Any


class NovaError(Exception):
    """Base exception for all Nova-specific errors."""
    
    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Error message
            stage: Processing stage where error occurred
            details: Additional error details
            recoverable: Whether the error is potentially recoverable
        """
        super().__init__(message)
        self.message = message
        self.stage = stage
        self.details = details or {}
        self.recoverable = recoverable


class ValidationError(NovaError):
    """Error during document validation."""
    pass


class ProcessingError(NovaError):
    """Error during document processing."""
    pass


class ConsolidationError(NovaError):
    """Error during document consolidation."""
    pass


class PDFGenerationError(NovaError):
    """Error during PDF generation."""
    pass


class ConfigurationError(NovaError):
    """Error in configuration."""
    pass


class ResourceError(NovaError):
    """Error during resource management."""
    pass


class PipelineError(NovaError):
    """Error in the processing pipeline."""
    pass


class ConversionError(NovaError):
    """Error during document conversion."""
    pass


class FileOperationError(NovaError):
    """Error during file operations."""
    pass


class TemplateError(NovaError):
    """Error during template processing."""
    pass
