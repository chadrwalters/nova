"""Error definitions for Nova Document Processor."""

from enum import Enum

class ErrorSeverity(str, Enum):
    """Error severity levels."""
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class NovaError(Exception):
    """Base exception for Nova Document Processor."""
    def __init__(self, message: str, severity: ErrorSeverity = ErrorSeverity.ERROR):
        self.message = message
        self.severity = severity
        super().__init__(self.message)

class ConfigError(NovaError):
    """Configuration related errors."""
    pass

class ValidationError(NovaError):
    """Validation related errors."""
    pass

class ProcessingError(NovaError):
    """Document processing errors."""
    pass