"""Error types and codes."""

from enum import Enum


class ErrorCode(str, Enum):
    """Error codes."""

    UNKNOWN = "UNKNOWN"
    INVALID_REQUEST = "INVALID_REQUEST"
    RESOURCE_NOT_FOUND = "RESOURCE_NOT_FOUND"
    RESOURCE_EXISTS = "RESOURCE_EXISTS"
    RESOURCE_ERROR = "RESOURCE_ERROR"
    STORE_ERROR = "STORE_ERROR"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    CONFIGURATION_ERROR = "CONFIGURATION_ERROR"
    NETWORK_ERROR = "NETWORK_ERROR"
    TIMEOUT_ERROR = "TIMEOUT_ERROR"
    SYSTEM_ERROR = "SYSTEM_ERROR"


class ResourceError(Exception):
    """Base class for resource errors."""

    def __init__(
        self, message: str, code: ErrorCode = ErrorCode.RESOURCE_ERROR
    ) -> None:
        """Initialize error.

        Args:
            message: Error message
            code: Error code
        """
        super().__init__(message)
        self.code = code
        self.message = message


class ValidationError(ResourceError):
    """Validation error."""

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message
        """
        super().__init__(message, ErrorCode.VALIDATION_ERROR)


class PermissionError(ResourceError):
    """Permission error."""

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message
        """
        super().__init__(message, ErrorCode.PERMISSION_ERROR)


class ConfigurationError(ResourceError):
    """Configuration error."""

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message
        """
        super().__init__(message, ErrorCode.CONFIGURATION_ERROR)


class NetworkError(ResourceError):
    """Network error."""

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message
        """
        super().__init__(message, ErrorCode.NETWORK_ERROR)


class TimeoutError(ResourceError):
    """Timeout error."""

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message
        """
        super().__init__(message, ErrorCode.TIMEOUT_ERROR)


class SystemError(ResourceError):
    """System error."""

    def __init__(self, message: str) -> None:
        """Initialize error.

        Args:
            message: Error message
        """
        super().__init__(message, ErrorCode.SYSTEM_ERROR)
