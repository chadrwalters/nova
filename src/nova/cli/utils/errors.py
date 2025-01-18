"""Error handling utilities for Nova CLI."""

from dataclasses import dataclass
from enum import Enum, auto
from typing import Any


class RebuildErrorType(Enum):
    """Types of rebuild errors."""

    INITIALIZATION = auto()  # Error during rebuild initialization
    CLEANUP = auto()  # Error during cleanup phase
    PROCESSING = auto()  # Error during note processing
    VECTOR_STORE = auto()  # Error with vector store operations
    RESOURCE = auto()  # Resource-related errors (memory, disk, etc.)
    VALIDATION = auto()  # Error during validation checks
    UNKNOWN = auto()  # Unknown or unclassified errors


@dataclass
class RebuildError(Exception):
    """Error during rebuild operations.

    Attributes:
        error_type: Type of rebuild error
        message: Error message
        context: Additional context about the error
        is_recoverable: Whether the error can be recovered from
        recovery_hint: Hint for recovery if applicable
    """

    error_type: RebuildErrorType
    message: str
    context: dict[str, Any]
    is_recoverable: bool = False
    recovery_hint: str | None = None

    def __str__(self) -> str:
        """Get string representation of the error.

        Returns:
            Formatted error message with context
        """
        error_str = f"[{self.error_type.name}] {self.message}"
        if self.context:
            error_str += f"\nContext: {self.context}"
        if self.is_recoverable and self.recovery_hint:
            error_str += f"\nRecovery hint: {self.recovery_hint}"
        return error_str


def create_rebuild_error(
    error_type: RebuildErrorType,
    message: str,
    context: dict[str, Any],
    is_recoverable: bool = False,
    recovery_hint: str | None = None,
) -> RebuildError:
    """Create a RebuildError with the given parameters.

    Args:
        error_type: Type of rebuild error
        message: Error message
        context: Additional context about the error
        is_recoverable: Whether the error can be recovered from
        recovery_hint: Hint for recovery if applicable

    Returns:
        RebuildError instance
    """
    return RebuildError(
        error_type=error_type,
        message=message,
        context=context,
        is_recoverable=is_recoverable,
        recovery_hint=recovery_hint,
    )


def is_recoverable_error(error: Exception) -> bool:
    """Check if an error is recoverable.

    Args:
        error: Exception to check

    Returns:
        True if error is recoverable, False otherwise
    """
    if isinstance(error, RebuildError):
        return error.is_recoverable

    # Add checks for other recoverable error types
    recoverable_errors = (
        FileNotFoundError,  # Missing files can be recreated
        PermissionError,  # Permissions can be fixed
        TimeoutError,  # Operations can be retried
    )
    return isinstance(error, recoverable_errors)


def get_recovery_strategy(error: RebuildError) -> str | None:
    """Get recovery strategy for a rebuild error.

    Args:
        error: RebuildError to get strategy for

    Returns:
        Recovery strategy if available, None otherwise
    """
    if not error.is_recoverable:
        return None

    # Return custom recovery hint if provided
    if error.recovery_hint:
        return error.recovery_hint

    # Default strategies based on error type
    strategies = {
        RebuildErrorType.INITIALIZATION: "Verify system configuration and try again",
        RebuildErrorType.CLEANUP: "Manually clean directories and retry",
        RebuildErrorType.PROCESSING: "Check input files and retry failed items",
        RebuildErrorType.VECTOR_STORE: "Verify vector store integrity and retry",
        RebuildErrorType.RESOURCE: "Free up system resources and retry",
        RebuildErrorType.VALIDATION: "Fix validation errors and retry",
    }
    return strategies.get(error.error_type)
