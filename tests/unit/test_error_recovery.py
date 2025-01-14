"""Tests for error recovery module."""

from unittest.mock import Mock
from typing import cast

import pytest

from nova.server.errors import ErrorCode, ResourceError
from nova.server.resources.error_recovery import (
    retry_on_error,
    graceful_degradation,
    with_fallback_options,
)


def test_retry_on_error_success() -> None:
    """Test successful retry after failures."""
    mock_func = Mock()
    mock_func.side_effect = [ValueError("Error"), ValueError("Error"), "success"]

    @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
    def test_func() -> str:
        return cast(str, mock_func())

    result = test_func()
    assert result == "success"
    assert mock_func.call_count == 3


def test_retry_on_error_failure() -> None:
    """Test retry exhaustion."""
    mock_func = Mock()
    mock_func.side_effect = ValueError("Persistent error")

    @retry_on_error(max_retries=2, delay=0.1, backoff=1.0)
    def test_func() -> None:
        mock_func()

    with pytest.raises(ResourceError) as exc:
        test_func()

    assert mock_func.call_count == 3
    assert "Persistent error" in str(exc.value)
    assert exc.value.code == ErrorCode.RESOURCE_ERROR


def test_graceful_degradation_success() -> None:
    """Test successful primary function."""
    mock_func = Mock()
    mock_func.return_value = "success"
    mock_fallback = Mock()

    @graceful_degradation(fallback_func=mock_fallback)
    def test_func() -> str:
        return cast(str, mock_func())

    result = test_func()
    assert result == "success"
    mock_func.assert_called_once()
    mock_fallback.assert_not_called()


def test_graceful_degradation_fallback_success() -> None:
    """Test successful fallback after primary failure."""
    mock_func = Mock(side_effect=ValueError("Primary error"))
    mock_fallback = Mock()
    mock_fallback.return_value = "fallback success"

    @graceful_degradation(fallback_func=mock_fallback)
    def test_func() -> str:
        return cast(str, mock_func())

    result = test_func()
    assert result == "fallback success"
    mock_func.assert_called_once()
    mock_fallback.assert_called_once()


def test_graceful_degradation_all_failure() -> None:
    """Test both primary and fallback failure."""
    mock_func = Mock(side_effect=ValueError("Primary error"))
    mock_fallback = Mock(side_effect=ValueError("Fallback error"))

    @graceful_degradation(fallback_func=mock_fallback)
    def test_func() -> None:
        mock_func()

    with pytest.raises(ResourceError) as exc:
        test_func()

    mock_func.assert_called_once()
    mock_fallback.assert_called_once()
    assert "Primary error" in str(exc.value)
    assert "Fallback error" in str(exc.value)
    assert exc.value.code == ErrorCode.RESOURCE_ERROR


def test_graceful_degradation_no_fallback() -> None:
    """Test failure with no fallback function."""
    mock_func = Mock(side_effect=ValueError("Error"))

    @graceful_degradation()
    def test_func() -> None:
        mock_func()

    with pytest.raises(ResourceError) as exc:
        test_func()

    mock_func.assert_called_once()
    assert "Error" in str(exc.value)
    assert exc.value.code == ErrorCode.RESOURCE_ERROR


def test_with_fallback_options_success() -> None:
    """Test successful primary function with options."""
    mock_primary = Mock()
    mock_primary.return_value = "success"
    mock_fallback1 = Mock()
    mock_fallback2 = Mock()

    @with_fallback_options([mock_fallback1, mock_fallback2])
    def test_func() -> str:
        return cast(str, mock_primary())

    result = test_func()
    assert result == "success"
    mock_primary.assert_called_once()
    mock_fallback1.assert_not_called()
    mock_fallback2.assert_not_called()


def test_with_fallback_options_first_fallback() -> None:
    """Test successful first fallback after primary failure."""
    mock_primary = Mock(side_effect=ValueError("Primary error"))
    mock_fallback1 = Mock()
    mock_fallback1.return_value = "fallback1 success"
    mock_fallback2 = Mock()

    @with_fallback_options([mock_fallback1, mock_fallback2])
    def test_func() -> str:
        return cast(str, mock_primary())

    result = test_func()
    assert result == "fallback1 success"
    mock_primary.assert_called_once()
    mock_fallback1.assert_called_once()
    mock_fallback2.assert_not_called()


def test_with_fallback_options_second_fallback() -> None:
    """Test successful second fallback after primary and first fallback
    failure."""
    mock_primary = Mock(side_effect=ValueError("Primary error"))
    mock_fallback1 = Mock(side_effect=ValueError("Fallback1 error"))
    mock_fallback2 = Mock()
    mock_fallback2.return_value = "fallback2 success"

    @with_fallback_options([mock_fallback1, mock_fallback2])
    def test_func() -> str:
        return cast(str, mock_primary())

    result = test_func()
    assert result == "fallback2 success"
    mock_primary.assert_called_once()
    mock_fallback1.assert_called_once()
    mock_fallback2.assert_called_once()


def test_with_fallback_options_all_failure() -> None:
    """Test all options failing."""
    mock_primary = Mock(side_effect=ValueError("Primary error"))
    mock_fallback1 = Mock(side_effect=ValueError("Fallback1 error"))
    mock_fallback2 = Mock(side_effect=ValueError("Fallback2 error"))

    @with_fallback_options([mock_fallback1, mock_fallback2])
    def test_func() -> None:
        mock_primary()

    with pytest.raises(ResourceError) as exc:
        test_func()

    mock_primary.assert_called_once()
    mock_fallback1.assert_called_once()
    mock_fallback2.assert_called_once()
    assert "Primary error" in str(exc.value)
    assert "Fallback1 error" in str(exc.value)
    assert "Fallback2 error" in str(exc.value)
    assert exc.value.code == ErrorCode.RESOURCE_ERROR
