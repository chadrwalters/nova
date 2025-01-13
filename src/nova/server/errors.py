"""Error handling for Nova server."""

from enum import Enum
from typing import Any, TypedDict


class ErrorDetails(TypedDict, total=False):
    """Error details type."""

    resource_id: str
    tool_id: str
    message_id: str
    confidence: float
    query: str
    error: str
    timestamp: float


class ErrorCode(Enum):
    """Error codes for Nova server."""

    # General errors (1000-1999)
    UNKNOWN_ERROR = 1000
    INVALID_REQUEST = 1001
    UNAUTHORIZED = 1002
    RATE_LIMITED = 1003
    INTERNAL_ERROR = 1004

    # Resource errors (2000-2999)
    RESOURCE_NOT_FOUND = 2000
    RESOURCE_ALREADY_EXISTS = 2001
    RESOURCE_ACCESS_DENIED = 2002
    RESOURCE_INVALID_STATE = 2003
    RESOURCE_OPERATION_FAILED = 2004

    # Tool errors (3000-3999)
    TOOL_NOT_FOUND = 3000
    TOOL_EXECUTION_FAILED = 3001
    TOOL_INVALID_PARAMS = 3002
    TOOL_TIMEOUT = 3003

    # Protocol errors (4000-4999)
    PROTOCOL_ERROR = 4000
    INVALID_MESSAGE = 4001
    CONNECTION_ERROR = 4002
    WEBSOCKET_ERROR = 4003

    # OCR errors (5000-5999)
    OCR_PROCESSING_FAILED = 5000
    OCR_LOW_CONFIDENCE = 5001
    OCR_INVALID_IMAGE = 5002
    OCR_ENGINE_ERROR = 5003

    # Vector store errors (6000-6999)
    VECTOR_STORE_ERROR = 6000
    VECTOR_STORE_QUERY_FAILED = 6001
    VECTOR_STORE_INSERT_FAILED = 6002
    VECTOR_STORE_DELETE_FAILED = 6003

    @property
    def recovery_hint(self) -> str:
        """Get default recovery hint for error code.

        Returns:
            Recovery hint string
        """
        DEFAULT_HINT = "An unknown error occurred. Please try again."
        hints: dict[ErrorCode, str] = {
            # General errors
            ErrorCode.UNKNOWN_ERROR: "Please try again or contact support if the issue persists.",
            ErrorCode.INVALID_REQUEST: "Check the request parameters and try again.",
            ErrorCode.UNAUTHORIZED: "Verify your API key and permissions.",
            ErrorCode.RATE_LIMITED: "Please wait and try again later.",
            ErrorCode.INTERNAL_ERROR: "An internal error occurred. Please try again or contact support.",
            # Resource errors
            ErrorCode.RESOURCE_NOT_FOUND: "Verify the resource ID and try again.",
            ErrorCode.RESOURCE_ALREADY_EXISTS: "Use a different resource ID or update the existing resource.",
            ErrorCode.RESOURCE_ACCESS_DENIED: "Check your permissions for this resource.",
            ErrorCode.RESOURCE_INVALID_STATE: "The resource is in an invalid state. Try resetting it.",
            ErrorCode.RESOURCE_OPERATION_FAILED: "The operation failed. Check the error details and try again.",
            # Tool errors
            ErrorCode.TOOL_NOT_FOUND: "Verify the tool ID and try again.",
            ErrorCode.TOOL_EXECUTION_FAILED: "Check the tool parameters and try again.",
            ErrorCode.TOOL_INVALID_PARAMS: "Fix the invalid parameters and try again.",
            ErrorCode.TOOL_TIMEOUT: "The operation timed out. Try again with a longer timeout.",
            # Protocol errors
            ErrorCode.PROTOCOL_ERROR: "A protocol error occurred. Check your client implementation.",
            ErrorCode.INVALID_MESSAGE: "Fix the message format and try again.",
            ErrorCode.CONNECTION_ERROR: "Check your network connection and try again.",
            ErrorCode.WEBSOCKET_ERROR: "The WebSocket connection failed. Try reconnecting.",
            # OCR errors
            ErrorCode.OCR_PROCESSING_FAILED: "OCR processing failed. Try with a different image.",
            ErrorCode.OCR_LOW_CONFIDENCE: "Low confidence in OCR results. Try improving image quality.",
            ErrorCode.OCR_INVALID_IMAGE: "The image format is invalid. Use a supported format.",
            ErrorCode.OCR_ENGINE_ERROR: "OCR engine error. Try with different settings.",
            # Vector store errors
            ErrorCode.VECTOR_STORE_ERROR: "Vector store operation failed. Check the store state.",
            ErrorCode.VECTOR_STORE_QUERY_FAILED: "Query failed. Check the query syntax.",
            ErrorCode.VECTOR_STORE_INSERT_FAILED: "Insert failed. Verify the data format.",
            ErrorCode.VECTOR_STORE_DELETE_FAILED: "Delete failed. Check if vectors exist.",
        }
        return hints.get(self, DEFAULT_HINT)


class NovaError(Exception):
    """Base exception for Nova server errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.UNKNOWN_ERROR,
        details: ErrorDetails | None = None,
        recovery_hint: str | None = None,
    ) -> None:
        """Initialize error.

        Args:
            message: Error message
            code: Error code
            details: Additional error details
            recovery_hint: Hint for error recovery
        """
        super().__init__(message)
        self.code = code
        self.details = details or {}
        self.recovery_hint = recovery_hint or code.recovery_hint

    def to_dict(self) -> dict[str, Any]:
        """Convert error to dictionary.

        Returns:
            Error dictionary
        """
        return {
            "code": self.code.value,
            "message": str(self),
            "details": self.details,
            "recovery_hint": self.recovery_hint,
        }


class ResourceError(NovaError):
    """Resource-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.RESOURCE_OPERATION_FAILED,
        details: ErrorDetails | None = None,
        recovery_hint: str | None = None,
    ) -> None:
        """Initialize resource error."""
        super().__init__(message, code, details, recovery_hint)


class ToolError(NovaError):
    """Tool-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.TOOL_EXECUTION_FAILED,
        details: ErrorDetails | None = None,
        recovery_hint: str | None = None,
    ) -> None:
        """Initialize tool error."""
        super().__init__(message, code, details, recovery_hint)


class ProtocolError(NovaError):
    """Protocol-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.PROTOCOL_ERROR,
        details: ErrorDetails | None = None,
        recovery_hint: str | None = None,
    ) -> None:
        """Initialize protocol error."""
        super().__init__(message, code, details, recovery_hint)


class OCRError(NovaError):
    """OCR-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.OCR_PROCESSING_FAILED,
        details: ErrorDetails | None = None,
        recovery_hint: str | None = None,
    ) -> None:
        """Initialize OCR error."""
        super().__init__(message, code, details, recovery_hint)


class VectorStoreError(NovaError):
    """Vector store-related errors."""

    def __init__(
        self,
        message: str,
        code: ErrorCode = ErrorCode.VECTOR_STORE_ERROR,
        details: ErrorDetails | None = None,
        recovery_hint: str | None = None,
    ) -> None:
        """Initialize vector store error."""
        super().__init__(message, code, details, recovery_hint)
