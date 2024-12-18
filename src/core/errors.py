from typing import Optional, Dict, Any, List
import logging
import structlog
from .base_config import ErrorSeverity

logger = structlog.get_logger(__name__)

class NovaError(Exception):
    """Base exception class for Nova."""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)

class ConfigError(NovaError):
    """Configuration related errors."""
    pass

class ValidationError(NovaError):
    """Validation related errors."""
    pass

class ProcessingError(NovaError):
    """Document processing related errors."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR, source: str = "", details: Optional[Dict[str, Any]] = None):
        self.severity = severity
        self.source = source
        super().__init__(message, details)

class MarkdownError(NovaError):
    """Markdown processing related errors."""
    pass

class PDFError(NovaError):
    """PDF generation related errors."""
    pass

class PDFGenerationError(PDFError):
    """PDF generation specific errors."""
    pass

class PDFStyleError(PDFError):
    """PDF styling related errors."""
    pass

class PDFContentError(PDFError):
    """PDF content related errors."""
    pass

class ErrorHandler:
    """Handle and track processing errors."""
    def __init__(self, tolerance: str = "lenient"):
        self.tolerance = tolerance
        self.errors: List[ProcessingError] = []
        
    def add_error(self, error: ProcessingError) -> None:
        """Add an error and log it."""
        self.errors.append(error)
        getattr(logger, error.severity.value)(
            error.message,
            source=error.source,
            **(error.details or {})
        )
        
    def get_errors(self, min_severity: ErrorSeverity = ErrorSeverity.WARNING) -> List[ProcessingError]:
        """Get all errors at or above specified severity."""
        return [e for e in self.errors if e.severity.to_logging_level() >= min_severity.to_logging_level()]
        
    def has_errors(self, min_severity: ErrorSeverity = ErrorSeverity.ERROR) -> bool:
        """Check if there are any errors at or above specified severity."""
        return any(e.severity.to_logging_level() >= min_severity.to_logging_level() for e in self.errors)

def format_error_message(error_msg: str, title: str, path: str) -> str:
    """Format error message in markdown."""
    return f"""
> **Error**: {error_msg}
> - Title: {title}
> - Path: {path}
> Please check the document and try again.
"""