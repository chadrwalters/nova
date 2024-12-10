"""Custom exceptions for the document processing pipeline."""

from typing import Optional, List, Dict, Any


class NovaError(Exception):
    """Base exception for all Nova-specific errors."""
    
    def __init__(
        self,
        message: str,
        error_code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None,
        recoverable: bool = False
    ) -> None:
        """Initialize the exception.
        
        Args:
            message: Error message
            error_code: Optional error code for categorization
            details: Additional error details
            recoverable: Whether the error is potentially recoverable
        """
        super().__init__(message)
        self.error_code = error_code or "NOVA_ERROR"
        self.details = details or {}
        self.recoverable = recoverable


class ValidationError(NovaError):
    """Raised when content validation fails."""
    
    def __init__(
        self,
        message: str,
        issues: Optional[List[str]] = None,
        **kwargs
    ) -> None:
        """Initialize validation error.
        
        Args:
            message: Error message
            issues: List of validation issues
            **kwargs: Additional arguments for NovaError
        """
        super().__init__(
            message,
            error_code="VALIDATION_ERROR",
            details={"issues": issues or []},
            **kwargs
        )
        self.issues = issues or []


class ProcessingError(NovaError):
    """Raised when document processing fails."""
    
    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize processing error.
        
        Args:
            message: Error message
            stage: Processing stage where error occurred
            **kwargs: Additional arguments for NovaError
        """
        super().__init__(
            message,
            error_code="PROCESSING_ERROR",
            details={"stage": stage},
            **kwargs
        )
        self.stage = stage


class ResourceError(NovaError):
    """Raised when resource management fails."""
    
    def __init__(
        self,
        message: str,
        resource_type: Optional[str] = None,
        resource_path: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize resource error.
        
        Args:
            message: Error message
            resource_type: Type of resource (file, memory, etc.)
            resource_path: Path to the resource if applicable
            **kwargs: Additional arguments for NovaError
        """
        super().__init__(
            message,
            error_code="RESOURCE_ERROR",
            details={
                "resource_type": resource_type,
                "resource_path": resource_path
            },
            **kwargs
        )
        self.resource_type = resource_type
        self.resource_path = resource_path


class ConfigurationError(NovaError):
    """Raised when configuration is invalid or missing."""
    
    def __init__(
        self,
        message: str,
        config_key: Optional[str] = None,
        **kwargs
    ) -> None:
        """Initialize configuration error.
        
        Args:
            message: Error message
            config_key: Configuration key that caused the error
            **kwargs: Additional arguments for NovaError
        """
        super().__init__(
            message,
            error_code="CONFIG_ERROR",
            details={"config_key": config_key},
            **kwargs
        )
        self.config_key = config_key


class PipelineError(NovaError):
    """Raised when the processing pipeline fails."""
    
    def __init__(
        self,
        message: str,
        stage: Optional[str] = None,
        recoverable: bool = True,
        **kwargs
    ) -> None:
        """Initialize pipeline error.
        
        Args:
            message: Error message
            stage: Pipeline stage where error occurred
            recoverable: Whether pipeline can continue
            **kwargs: Additional arguments for NovaError
        """
        super().__init__(
            message,
            error_code="PIPELINE_ERROR",
            details={"stage": stage},
            recoverable=recoverable,
            **kwargs
        )
        self.stage = stage


"""Custom exceptions for the application."""

class NovaError(Exception):
    """Base exception class for Nova application."""
    
    def __init__(self, message: str, **kwargs) -> None:
        self.message = message
        self.details = kwargs
        super().__init__(message)

class ValidationError(NovaError):
    """Raised when validation fails."""
    pass

class FileSizeError(ValidationError):
    """Raised when file size exceeds limits."""
    pass

class EncodingError(ValidationError):
    """Raised when file encoding is invalid or unsupported."""
    pass

class MalformedMarkdownError(ValidationError):
    """Raised when markdown content is malformed."""
    pass

class ResourceError(NovaError):
    """Raised when resource management fails."""
    
    def __init__(
        self, 
        message: str, 
        resource_type: str,
        resource_path: str | None = None
    ) -> None:
        super().__init__(
            message,
            resource_type=resource_type,
            resource_path=resource_path
        )

class ProcessingError(NovaError):
    """Raised when document processing fails."""
    pass

class ConsolidationError(NovaError):
    """Raised when document consolidation fails."""
    pass

class ConfigurationError(NovaError):
    """Raised when configuration is invalid."""
    pass

class FileOperationError(NovaError):
    """Raised when file operations fail."""
    pass

class TemplateError(NovaError):
    """Raised when template processing fails."""
    pass

class ConversionError(NovaError):
    """Raised when document conversion fails."""
    pass

class LockError(ResourceError):
    """Raised when file locking fails."""
    pass

class CleanupError(ResourceError):
    """Raised when resource cleanup fails."""
    pass

class MemoryError(ResourceError):
    """Raised when memory limits are exceeded."""
    pass

class StorageError(ResourceError):
    """Raised when storage limits are exceeded."""
    pass
