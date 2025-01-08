"""Error handling for Nova document processing."""
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional


class ErrorSeverity(Enum):
    """Severity levels for errors."""

    DEBUG = "debug"  # Development-time issues
    INFO = "info"  # Non-critical information
    WARNING = "warning"  # Non-fatal issues that should be addressed
    ERROR = "error"  # Fatal issues that prevent processing
    CRITICAL = "critical"  # System-level failures


class ErrorCategory(Enum):
    """Categories of errors that can occur."""

    CONFIGURATION = "configuration"  # Config file, env vars, etc.
    FILESYSTEM = "filesystem"  # File access, permissions, etc.
    VALIDATION = "validation"  # Data validation issues
    PROCESSING = "processing"  # Document processing errors
    REFERENCE = "reference"  # Link/reference related errors
    SYSTEM = "system"  # System-level errors
    HANDLER = "handler"  # Handler-specific errors
    PHASE = "phase"  # Phase-specific errors
    PIPELINE = "pipeline"  # Pipeline-level errors


class ErrorContext:
    """Context information for errors."""

    def __init__(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        phase: Optional[str] = None,
        handler: Optional[str] = None,
        file_path: Optional[Path] = None,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None,
        stack_trace: Optional[str] = None,
        system_state: Optional[Dict[str, Any]] = None,
        related_files: Optional[List[Path]] = None,
        error_chain: Optional[List["ErrorContext"]] = None,
    ) -> None:
        """Initialize error context.

        Args:
            category: Error category
            severity: Error severity
            message: Error message
            phase: Optional phase name where error occurred
            handler: Optional handler name where error occurred
            file_path: Optional file path related to error
            details: Optional additional error details
            recovery_hint: Optional suggestion for recovery
            original_error: Optional original exception
            stack_trace: Optional formatted stack trace
            system_state: Optional dict of relevant system state (memory, disk, etc)
            related_files: Optional list of related file paths
            error_chain: Optional list of previous errors that led to this one
        """
        self.category = category
        self.severity = severity
        self.message = message
        self.phase = phase
        self.handler = handler
        self.file_path = file_path
        self.details = details or {}
        self.recovery_hint = recovery_hint
        self.original_error = original_error
        self.stack_trace = stack_trace
        self.system_state = system_state or {}
        self.related_files = related_files or []
        self.error_chain = error_chain or []

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary.

        Returns:
            Dictionary representation of context
        """
        return {
            "category": self.category.value,
            "severity": self.severity.value,
            "message": self.message,
            "phase": self.phase,
            "handler": self.handler,
            "file_path": str(self.file_path) if self.file_path else None,
            "details": self.details,
            "recovery_hint": self.recovery_hint,
            "original_error": str(self.original_error) if self.original_error else None,
            "stack_trace": self.stack_trace,
            "system_state": self.system_state,
            "related_files": [str(f) for f in self.related_files],
            "error_chain": [e.to_dict() for e in self.error_chain],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ErrorContext":
        """Create context from dictionary.

        Args:
            data: Dictionary representation of context

        Returns:
            ErrorContext instance
        """
        error_chain = []
        if data.get("error_chain"):
            error_chain = [cls.from_dict(e) for e in data["error_chain"]]

        return cls(
            category=ErrorCategory(data["category"]),
            severity=ErrorSeverity(data["severity"]),
            message=data["message"],
            phase=data.get("phase"),
            handler=data.get("handler"),
            file_path=Path(data["file_path"]) if data.get("file_path") else None,
            details=data.get("details", {}),
            recovery_hint=data.get("recovery_hint"),
            original_error=Exception(data["original_error"])
            if data.get("original_error")
            else None,
            stack_trace=data.get("stack_trace"),
            system_state=data.get("system_state", {}),
            related_files=[Path(f) for f in data.get("related_files", [])],
            error_chain=error_chain,
        )


class NovaError(Exception):
    """Base exception for Nova errors."""

    def __init__(
        self,
        context: ErrorContext,
    ) -> None:
        """Initialize error.

        Args:
            context: Error context
        """
        super().__init__(context.message)
        self.context = context

    def to_dict(self) -> Dict[str, Any]:
        """Convert error to dictionary.

        Returns:
            Dictionary representation of error
        """
        return self.context.to_dict()

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "NovaError":
        """Create error from dictionary.

        Args:
            data: Dictionary representation of error

        Returns:
            NovaError instance
        """
        return cls(ErrorContext.from_dict(data))


class ConfigurationError(NovaError):
    """Error in configuration."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            ErrorContext(
                category=ErrorCategory.CONFIGURATION,
                severity=ErrorSeverity.ERROR,
                message=message,
                details=details,
                recovery_hint=recovery_hint,
                original_error=original_error,
            )
        )


class HandlerError(NovaError):
    """Error in document handler."""

    def __init__(
        self,
        message: str,
        handler: str,
        file_path: Optional[Path] = None,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            ErrorContext(
                category=ErrorCategory.HANDLER,
                severity=ErrorSeverity.ERROR,
                message=message,
                handler=handler,
                file_path=file_path,
                details=details,
                recovery_hint=recovery_hint,
                original_error=original_error,
            )
        )


class PhaseError(NovaError):
    """Error in processing phase."""

    def __init__(
        self,
        message: str,
        phase: str,
        file_path: Optional[Path] = None,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            ErrorContext(
                category=ErrorCategory.PHASE,
                severity=ErrorSeverity.ERROR,
                message=message,
                phase=phase,
                file_path=file_path,
                details=details,
                recovery_hint=recovery_hint,
                original_error=original_error,
            )
        )


class ValidationError(NovaError):
    """Error in data validation."""

    def __init__(
        self,
        message: str,
        phase: Optional[str] = None,
        handler: Optional[str] = None,
        file_path: Optional[Path] = None,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            ErrorContext(
                category=ErrorCategory.VALIDATION,
                severity=ErrorSeverity.ERROR,
                message=message,
                phase=phase,
                handler=handler,
                file_path=file_path,
                details=details,
                recovery_hint=recovery_hint,
                original_error=original_error,
            )
        )


class ResourceError(NovaError):
    """Error accessing resources."""

    def __init__(
        self,
        message: str,
        file_path: Optional[Path] = None,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            ErrorContext(
                category=ErrorCategory.FILESYSTEM,
                severity=ErrorSeverity.ERROR,
                message=message,
                file_path=file_path,
                details=details,
                recovery_hint=recovery_hint,
                original_error=original_error,
            )
        )


class ProcessingError(NovaError):
    """Error during document processing."""

    def __init__(
        self,
        message: str,
        phase: Optional[str] = None,
        handler: Optional[str] = None,
        file_path: Optional[Path] = None,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            ErrorContext(
                category=ErrorCategory.PROCESSING,
                severity=ErrorSeverity.ERROR,
                message=message,
                phase=phase,
                handler=handler,
                file_path=file_path,
                details=details,
                recovery_hint=recovery_hint,
                original_error=original_error,
            )
        )


class IndexError(NovaError):
    """Error in search index operations."""

    def __init__(
        self,
        message: str,
        details: Optional[Dict[str, Any]] = None,
        recovery_hint: Optional[str] = None,
        original_error: Optional[Exception] = None,
    ) -> None:
        super().__init__(
            ErrorContext(
                category=ErrorCategory.SYSTEM,
                severity=ErrorSeverity.ERROR,
                message=message,
                details=details,
                recovery_hint=recovery_hint,
                original_error=original_error,
            )
        )


def wrap_error(
    error: Exception,
    message: str,
    category: ErrorCategory = ErrorCategory.SYSTEM,
    severity: ErrorSeverity = ErrorSeverity.ERROR,
    phase: Optional[str] = None,
    handler: Optional[str] = None,
    file_path: Optional[Path] = None,
    details: Optional[Dict[str, Any]] = None,
    recovery_hint: Optional[str] = None,
    related_files: Optional[List[Path]] = None,
    system_state: Optional[Dict[str, Any]] = None,
) -> NovaError:
    """Wrap an exception in a Nova error.

    Args:
        error: Original exception
        message: Error message
        category: Error category
        severity: Error severity
        phase: Optional phase name
        handler: Optional handler name
        file_path: Optional file path
        details: Optional error details
        recovery_hint: Optional recovery hint
        related_files: Optional list of related files
        system_state: Optional system state information

    Returns:
        Wrapped Nova error
    """
    import traceback

    import psutil

    # Get stack trace
    stack_trace = "".join(
        traceback.format_exception(type(error), error, error.__traceback__)
    )

    # Get basic system state if not provided
    if system_state is None:
        try:
            process = psutil.Process()
            system_state = {
                "memory_percent": process.memory_percent(),
                "cpu_percent": process.cpu_percent(),
                "open_files": len(process.open_files()),
                "threads": process.num_threads(),
            }
        except Exception:
            system_state = {}

    if isinstance(error, NovaError):
        # Update existing error with new context if provided
        context = error.context
        if phase:
            context.phase = phase
        if handler:
            context.handler = handler
        if file_path:
            context.file_path = file_path
        if details:
            context.details.update(details)
        if recovery_hint:
            context.recovery_hint = recovery_hint
        if related_files:
            context.related_files.extend(related_files)
        if system_state:
            context.system_state.update(system_state)
        context.stack_trace = stack_trace
        return error

    # Create new error with full context
    return NovaError(
        ErrorContext(
            category=category,
            severity=severity,
            message=message,
            phase=phase,
            handler=handler,
            file_path=file_path,
            details=details,
            recovery_hint=recovery_hint,
            original_error=error,
            stack_trace=stack_trace,
            system_state=system_state,
            related_files=related_files,
        )
    )
