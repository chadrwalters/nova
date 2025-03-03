"""
Unit tests for the logging utilities.

This module tests the structured logging utilities.
"""

import json
import logging
import sys
from io import StringIO
from unittest.mock import patch

import pytest

from nova.utils.logging import (
    StructuredLogFormatter,
    get_logger,
    log_with_context,
    setup_logging,
)


class TestStructuredLogFormatter:
    """Tests for the StructuredLogFormatter class."""

    def test_format_basic_record(self):
        """Test formatting a basic log record."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["module"] == "test_module"
        assert log_data["function"] == "test_function"
        assert log_data["line"] == 42
        assert "timestamp" in log_data

    def test_format_with_exception(self):
        """Test formatting a log record with an exception."""
        formatter = StructuredLogFormatter()
        try:
            raise ValueError("Test exception")
        except ValueError:
            record = logging.LogRecord(
                name="test_logger",
                level=logging.ERROR,
                pathname="test_file.py",
                lineno=42,
                msg="Error occurred",
                args=(),
                exc_info=sys.exc_info(),
            )
            record.module = "test_module"
            record.funcName = "test_function"

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "ERROR"
        assert log_data["message"] == "Error occurred"
        assert "exception" in log_data
        assert log_data["exception"]["type"] == "ValueError"
        assert log_data["exception"]["message"] == "Test exception"

    def test_format_with_extra(self):
        """Test formatting a log record with extra fields."""
        formatter = StructuredLogFormatter()
        record = logging.LogRecord(
            name="test_logger",
            level=logging.INFO,
            pathname="test_file.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None,
        )
        record.module = "test_module"
        record.funcName = "test_function"
        record.extra = {"user_id": "123", "request_id": "456"}

        formatted = formatter.format(record)
        log_data = json.loads(formatted)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"
        assert log_data["user_id"] == "123"
        assert log_data["request_id"] == "456"


class TestSetupLogging:
    """Tests for the setup_logging function."""

    @patch("sys.stdout", new_callable=StringIO)
    def test_setup_structured_logging(self, mock_stdout):
        """Test setting up structured logging."""
        setup_logging(level="INFO", structured=True)
        logger = logging.getLogger()

        # Check that the logger has the correct level
        assert logger.level == logging.INFO

        # Check that the logger has one handler
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]

        # Check that the handler is a StreamHandler
        assert isinstance(handler, logging.StreamHandler)

        # Check that the handler has the correct formatter
        assert isinstance(handler.formatter, StructuredLogFormatter)

        # Log a message and check that it's formatted as JSON
        logger.info("Test message")
        log_output = mock_stdout.getvalue()
        log_data = json.loads(log_output)

        assert log_data["level"] == "INFO"
        assert log_data["message"] == "Test message"

    @patch("sys.stdout", new_callable=StringIO)
    def test_setup_standard_logging(self, mock_stdout):
        """Test setting up standard logging."""
        setup_logging(level="DEBUG", structured=False)
        logger = logging.getLogger()

        # Check that the logger has the correct level
        assert logger.level == logging.DEBUG

        # Check that the logger has one handler
        assert len(logger.handlers) == 1
        handler = logger.handlers[0]

        # Check that the handler is a StreamHandler
        assert isinstance(handler, logging.StreamHandler)

        # Check that the handler has the correct formatter
        assert not isinstance(handler.formatter, StructuredLogFormatter)

    def test_invalid_log_level(self):
        """Test that an invalid log level raises an error."""
        with pytest.raises(ValueError):
            setup_logging(level="INVALID")


class TestGetLogger:
    """Tests for the get_logger function."""

    def test_get_logger(self):
        """Test getting a logger with a specific name."""
        logger = get_logger("test_logger")
        assert isinstance(logger, logging.Logger)
        assert logger.name == "test_logger"


class TestLogWithContext:
    """Tests for the log_with_context function."""

    @patch("logging.Logger.debug")
    def test_log_debug_with_context(self, mock_debug):
        """Test logging a debug message with context."""
        logger = logging.getLogger("test_logger")
        log_with_context(logger, "debug", "Debug message", {"user_id": "123"})
        mock_debug.assert_called_once_with(
            "Debug message", extra={"extra": {"user_id": "123"}}
        )

    @patch("logging.Logger.info")
    def test_log_info_with_context(self, mock_info):
        """Test logging an info message with context."""
        logger = logging.getLogger("test_logger")
        log_with_context(logger, "info", "Info message", {"user_id": "123"})
        mock_info.assert_called_once_with(
            "Info message", extra={"extra": {"user_id": "123"}}
        )

    @patch("logging.Logger.warning")
    def test_log_warning_with_context(self, mock_warning):
        """Test logging a warning message with context."""
        logger = logging.getLogger("test_logger")
        log_with_context(logger, "warning", "Warning message", {"user_id": "123"})
        mock_warning.assert_called_once_with(
            "Warning message", extra={"extra": {"user_id": "123"}}
        )

    @patch("logging.Logger.error")
    def test_log_error_with_context(self, mock_error):
        """Test logging an error message with context."""
        logger = logging.getLogger("test_logger")
        log_with_context(logger, "error", "Error message", {"user_id": "123"})
        mock_error.assert_called_once_with(
            "Error message", extra={"extra": {"user_id": "123"}}
        )

    @patch("logging.Logger.critical")
    def test_log_critical_with_context(self, mock_critical):
        """Test logging a critical message with context."""
        logger = logging.getLogger("test_logger")
        log_with_context(logger, "critical", "Critical message", {"user_id": "123"})
        mock_critical.assert_called_once_with(
            "Critical message", extra={"extra": {"user_id": "123"}}
        )

    @patch("logging.Logger.info")
    def test_log_with_no_context(self, mock_info):
        """Test logging a message with no context."""
        logger = logging.getLogger("test_logger")
        log_with_context(logger, "info", "Info message")
        mock_info.assert_called_once_with("Info message", extra={"extra": {}})
