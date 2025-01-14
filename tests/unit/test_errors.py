"""Tests for error handling module."""

from nova.server.errors import (
    ErrorCode,
    ResourceError,
    ValidationError,
    PermissionError,
    ConfigurationError,
    NetworkError,
    TimeoutError,
    SystemError,
)


def test_error_code_values() -> None:
    """Test error code values."""
    assert ErrorCode.UNKNOWN == "UNKNOWN"
    assert ErrorCode.INVALID_REQUEST == "INVALID_REQUEST"
    assert ErrorCode.RESOURCE_NOT_FOUND == "RESOURCE_NOT_FOUND"
    assert ErrorCode.RESOURCE_EXISTS == "RESOURCE_EXISTS"
    assert ErrorCode.RESOURCE_ERROR == "RESOURCE_ERROR"
    assert ErrorCode.STORE_ERROR == "STORE_ERROR"
    assert ErrorCode.VALIDATION_ERROR == "VALIDATION_ERROR"
    assert ErrorCode.PERMISSION_ERROR == "PERMISSION_ERROR"
    assert ErrorCode.CONFIGURATION_ERROR == "CONFIGURATION_ERROR"
    assert ErrorCode.NETWORK_ERROR == "NETWORK_ERROR"
    assert ErrorCode.TIMEOUT_ERROR == "TIMEOUT_ERROR"
    assert ErrorCode.SYSTEM_ERROR == "SYSTEM_ERROR"


def test_resource_error() -> None:
    """Test ResourceError."""
    error = ResourceError("Resource error")
    assert str(error) == "Resource error"
    assert error.code == ErrorCode.RESOURCE_ERROR
    assert error.message == "Resource error"

    error = ResourceError("Not found", ErrorCode.RESOURCE_NOT_FOUND)
    assert str(error) == "Not found"
    assert error.code == ErrorCode.RESOURCE_NOT_FOUND
    assert error.message == "Not found"


def test_validation_error() -> None:
    """Test ValidationError."""
    error = ValidationError("Invalid input")
    assert str(error) == "Invalid input"
    assert error.code == ErrorCode.VALIDATION_ERROR
    assert error.message == "Invalid input"


def test_permission_error() -> None:
    """Test PermissionError."""
    error = PermissionError("Access denied")
    assert str(error) == "Access denied"
    assert error.code == ErrorCode.PERMISSION_ERROR
    assert error.message == "Access denied"


def test_configuration_error() -> None:
    """Test ConfigurationError."""
    error = ConfigurationError("Invalid config")
    assert str(error) == "Invalid config"
    assert error.code == ErrorCode.CONFIGURATION_ERROR
    assert error.message == "Invalid config"


def test_network_error() -> None:
    """Test NetworkError."""
    error = NetworkError("Connection failed")
    assert str(error) == "Connection failed"
    assert error.code == ErrorCode.NETWORK_ERROR
    assert error.message == "Connection failed"


def test_timeout_error() -> None:
    """Test TimeoutError."""
    error = TimeoutError("Operation timed out")
    assert str(error) == "Operation timed out"
    assert error.code == ErrorCode.TIMEOUT_ERROR
    assert error.message == "Operation timed out"


def test_system_error() -> None:
    """Test SystemError."""
    error = SystemError("System failure")
    assert str(error) == "System failure"
    assert error.code == ErrorCode.SYSTEM_ERROR
    assert error.message == "System failure"
