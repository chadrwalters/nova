"""Tests for error handling module."""

from nova.server.errors import (
    ErrorCode,
    ErrorDetails,
    NovaError,
    ResourceError,
    ToolError,
    ProtocolError,
    OCRError,
    VectorStoreError,
)


def test_error_code_values() -> None:
    """Test error code values."""
    # Test general errors
    assert ErrorCode.UNKNOWN_ERROR.value == 1000
    assert ErrorCode.INVALID_REQUEST.value == 1001
    assert ErrorCode.UNAUTHORIZED.value == 1002
    assert ErrorCode.RATE_LIMITED.value == 1003
    assert ErrorCode.INTERNAL_ERROR.value == 1004

    # Test resource errors
    assert ErrorCode.RESOURCE_NOT_FOUND.value == 2000
    assert ErrorCode.RESOURCE_ALREADY_EXISTS.value == 2001
    assert ErrorCode.RESOURCE_ACCESS_DENIED.value == 2002
    assert ErrorCode.RESOURCE_INVALID_STATE.value == 2003
    assert ErrorCode.RESOURCE_OPERATION_FAILED.value == 2004


def test_error_code_recovery_hints() -> None:
    """Test error code recovery hints."""
    # Test general error hints
    assert "try again" in ErrorCode.UNKNOWN_ERROR.recovery_hint.lower()
    assert "check" in ErrorCode.INVALID_REQUEST.recovery_hint.lower()
    assert "verify" in ErrorCode.UNAUTHORIZED.recovery_hint.lower()
    assert "wait" in ErrorCode.RATE_LIMITED.recovery_hint.lower()

    # Test resource error hints
    assert "verify" in ErrorCode.RESOURCE_NOT_FOUND.recovery_hint.lower()
    assert "different" in ErrorCode.RESOURCE_ALREADY_EXISTS.recovery_hint.lower()
    assert "permissions" in ErrorCode.RESOURCE_ACCESS_DENIED.recovery_hint.lower()

    # Test unknown error code hint
    assert "try again" in ErrorCode.UNKNOWN_ERROR.recovery_hint.lower()


def test_nova_error_init() -> None:
    """Test NovaError initialization."""
    details: ErrorDetails = {
        "resource_id": "test",
        "error": "Test error",
        "timestamp": 1234567890.0,
    }
    error = NovaError(
        message="Test error",
        code=ErrorCode.UNKNOWN_ERROR,
        details=details,
        recovery_hint="Try again",
    )

    assert str(error) == "Test error"
    assert error.code == ErrorCode.UNKNOWN_ERROR
    assert error.details == details
    assert error.recovery_hint == "Try again"


def test_nova_error_defaults() -> None:
    """Test NovaError default values."""
    error = NovaError("Test error")

    assert str(error) == "Test error"
    assert error.code == ErrorCode.UNKNOWN_ERROR
    assert error.details == {}
    assert error.recovery_hint == ErrorCode.UNKNOWN_ERROR.recovery_hint


def test_nova_error_to_dict() -> None:
    """Test NovaError to_dict method."""
    details: ErrorDetails = {
        "resource_id": "test",
        "error": "Test error",
        "timestamp": 1234567890.0,
    }
    error = NovaError(
        message="Test error",
        code=ErrorCode.UNKNOWN_ERROR,
        details=details,
        recovery_hint="Try again",
    )

    error_dict = error.to_dict()
    assert error_dict["code"] == 1000
    assert error_dict["message"] == "Test error"
    assert error_dict["details"] == details
    assert error_dict["recovery_hint"] == "Try again"


def test_resource_error() -> None:
    """Test ResourceError."""
    details: ErrorDetails = {"resource_id": "test", "error": "Resource not found"}
    error = ResourceError(
        message="Resource error",
        code=ErrorCode.RESOURCE_NOT_FOUND,
        details=details,
        recovery_hint="Check resource ID",
    )

    assert str(error) == "Resource error"
    assert error.code == ErrorCode.RESOURCE_NOT_FOUND
    assert error.details == details
    assert error.recovery_hint == "Check resource ID"

    # Test default code and recovery hint
    error = ResourceError("Resource error")
    assert error.code == ErrorCode.RESOURCE_OPERATION_FAILED
    assert error.recovery_hint == ErrorCode.RESOURCE_OPERATION_FAILED.recovery_hint


def test_tool_error() -> None:
    """Test ToolError."""
    details: ErrorDetails = {"tool_id": "test", "error": "Tool not found"}
    error = ToolError(
        message="Tool error",
        code=ErrorCode.TOOL_NOT_FOUND,
        details=details,
        recovery_hint="Check tool ID",
    )

    assert str(error) == "Tool error"
    assert error.code == ErrorCode.TOOL_NOT_FOUND
    assert error.details == details
    assert error.recovery_hint == "Check tool ID"

    # Test default code and recovery hint
    error = ToolError("Tool error")
    assert error.code == ErrorCode.TOOL_EXECUTION_FAILED
    assert error.recovery_hint == ErrorCode.TOOL_EXECUTION_FAILED.recovery_hint


def test_protocol_error() -> None:
    """Test ProtocolError."""
    details: ErrorDetails = {"message_id": "test", "error": "Invalid message"}
    error = ProtocolError(
        message="Protocol error",
        code=ErrorCode.INVALID_MESSAGE,
        details=details,
        recovery_hint="Check message format",
    )

    assert str(error) == "Protocol error"
    assert error.code == ErrorCode.INVALID_MESSAGE
    assert error.details == details
    assert error.recovery_hint == "Check message format"

    # Test default code and recovery hint
    error = ProtocolError("Protocol error")
    assert error.code == ErrorCode.PROTOCOL_ERROR
    assert error.recovery_hint == ErrorCode.PROTOCOL_ERROR.recovery_hint


def test_ocr_error() -> None:
    """Test OCRError."""
    details: ErrorDetails = {"confidence": 0.4, "error": "Low confidence"}
    error = OCRError(
        message="OCR error",
        code=ErrorCode.OCR_LOW_CONFIDENCE,
        details=details,
        recovery_hint="Try different OCR settings",
    )

    assert str(error) == "OCR error"
    assert error.code == ErrorCode.OCR_LOW_CONFIDENCE
    assert error.details == details
    assert error.recovery_hint == "Try different OCR settings"

    # Test default code and recovery hint
    error = OCRError("OCR error")
    assert error.code == ErrorCode.OCR_PROCESSING_FAILED
    assert error.recovery_hint == ErrorCode.OCR_PROCESSING_FAILED.recovery_hint


def test_vector_store_error() -> None:
    """Test VectorStoreError."""
    details: ErrorDetails = {"query": "test", "error": "Query failed"}
    error = VectorStoreError(
        message="Vector store error",
        code=ErrorCode.VECTOR_STORE_QUERY_FAILED,
        details=details,
        recovery_hint="Check query syntax",
    )

    assert str(error) == "Vector store error"
    assert error.code == ErrorCode.VECTOR_STORE_QUERY_FAILED
    assert error.details == details
    assert error.recovery_hint == "Check query syntax"

    # Test default code and recovery hint
    error = VectorStoreError("Vector store error")
    assert error.code == ErrorCode.VECTOR_STORE_ERROR
    assert error.recovery_hint == ErrorCode.VECTOR_STORE_ERROR.recovery_hint
