"""Tests for Nova logging system."""

import logging
import os
from pathlib import Path
from typing import Generator

import pytest

from nova.logging import (
    LogLevel,
    configure_logging,
    get_component_logger,
    log_error,
    log_tool_call,
)


@pytest.fixture
def configured_logging(tmp_path: Path) -> Generator[None, None, None]:
    """Configure logging for tests.

    Args:
        tmp_path: Temporary directory for test

    Yields:
        None
    """
    # Change to temp dir so .nova/logs is created there
    original_dir = os.getcwd()
    os.chdir(tmp_path)
    configure_logging()
    yield
    # Reset logging
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    # Restore directory
    os.chdir(original_dir)


def test_get_component_logger() -> None:
    """Test getting a component logger."""
    logger = get_component_logger("test")
    assert isinstance(logger, logging.Logger)
    assert logger.name == "FastMCP.nova.test"  # FastMCP prefixes logger names


def test_log_error(configured_logging: None, tmp_path: Path) -> None:
    """Test error logging.

    Args:
        configured_logging: Configured logging fixture
        tmp_path: Temporary directory for test
    """
    logger = get_component_logger("test")

    # Test with exception
    try:
        raise ValueError("Test error")
    except ValueError as e:
        log_error(logger, "An error occurred", e)

    # Test without exception
    log_error(logger, "Another error")

    # Check log file
    log_file = tmp_path / ".nova" / "logs" / "nova.log"
    assert log_file.exists()
    with open(log_file) as f:
        log_lines = f.readlines()

    assert len(log_lines) == 2
    assert any("Test error" in line for line in log_lines)
    assert any("Another error" in line for line in log_lines)


def test_log_tool_call(configured_logging: None, tmp_path: Path) -> None:
    """Test tool call logging.

    Args:
        configured_logging: Configured logging fixture
        tmp_path: Temporary directory for test
    """
    logger = get_component_logger("test")
    tool_args = {"arg1": "value1", "arg2": 123}

    log_tool_call(logger, "test_tool", tool_args)

    # Check log file
    log_file = tmp_path / ".nova" / "logs" / "nova.log"
    assert log_file.exists()
    with open(log_file) as f:
        log_lines = f.readlines()

    assert len(log_lines) == 1
    log_line = log_lines[0]
    assert "Calling tool" in log_line
    assert "test_tool" in log_line
    assert "value1" in log_line
    assert "123" in log_line


def test_configure_logging_defaults(tmp_path: Path) -> None:
    """Test logging configuration with defaults.

    Args:
        tmp_path: Temporary directory
    """
    os.chdir(tmp_path)  # Change to temp dir so .nova/logs is created there
    configure_logging()  # Use defaults

    nova_logs = tmp_path / ".nova" / "logs"
    assert nova_logs.exists()
    assert nova_logs.is_dir()

    logger = get_component_logger("test")
    logger.info("Test message")

    log_file = nova_logs / "nova.log"
    assert log_file.exists()
    with open(log_file) as f:
        assert "Test message" in f.read()

    # Restore directory
    os.chdir(os.path.dirname(tmp_path))
