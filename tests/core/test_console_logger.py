import pytest
from datetime import datetime
from unittest.mock import MagicMock, patch

from rich.console import Console
from rich.progress import Progress
from rich.table import Table

from nova.core.console.logger import ConsoleLogger, LogLevel, LogContext, MessageBatch


@pytest.fixture
def console_logger():
    """Create a ConsoleLogger instance for testing."""
    return ConsoleLogger()


def test_log_context():
    """Test LogContext push and pop functionality."""
    context = LogContext()
    
    # Test initial state
    assert context.indent_level == 0
    assert not context.context_stack
    
    # Test push
    context.push("test_context")
    assert context.indent_level == 1
    assert context.context_stack == ["test_context"]
    
    # Test nested push
    context.push("nested_context")
    assert context.indent_level == 2
    assert context.context_stack == ["test_context", "nested_context"]
    
    # Test pop
    popped = context.pop()
    assert popped == "nested_context"
    assert context.indent_level == 1
    assert context.context_stack == ["test_context"]
    
    # Test pop empty
    context.pop()
    context.pop()  # Extra pop should not cause issues
    assert context.indent_level == 0
    assert not context.context_stack


def test_message_batch():
    """Test MessageBatch add and clear functionality."""
    batch = MessageBatch()
    timestamp = datetime.now()
    
    # Test add message
    batch.add(LogLevel.INFO, "test message", timestamp)
    assert len(batch.messages) == 1
    assert batch.messages[0] == {
        "level": LogLevel.INFO,
        "message": "test message",
        "timestamp": timestamp
    }
    
    # Test clear
    batch.clear()
    assert not batch.messages


def test_console_logger_basic_logging(console_logger):
    """Test basic logging functionality."""
    with patch.object(console_logger.console, 'print') as mock_print:
        console_logger.info("test message")
        mock_print.assert_called_once()
        
        # Verify the message format
        text = mock_print.call_args[0][0]
        assert "INFO" in str(text)
        assert "test message" in str(text)


def test_console_logger_batch_logging(console_logger):
    """Test batch logging functionality."""
    with patch.object(console_logger.console, 'print') as mock_print:
        # Add messages to batch
        console_logger.info("message 1", batch=True)
        console_logger.warning("message 2", batch=True)
        console_logger.error("message 3", batch=True)
        
        # Output batch
        console_logger.batch()
        
        # Verify table output
        mock_print.assert_called_once()
        table = mock_print.call_args[0][0]
        assert isinstance(table, Table)


def test_console_logger_progress(console_logger):
    """Test progress bar creation."""
    progress = console_logger.progress("Processing files")
    assert isinstance(progress, Progress)
    
    # Test that creating a new progress bar stops the old one
    with patch.object(progress, 'stop') as mock_stop:
        new_progress = console_logger.progress("New progress")
        mock_stop.assert_called_once()


def test_console_logger_table(console_logger):
    """Test table creation."""
    table = console_logger.table("Test Table")
    assert isinstance(table, Table)
    assert table.title == "Test Table"


def test_console_logger_context_manager(console_logger):
    """Test context manager functionality."""
    with patch.object(console_logger, 'batch') as mock_batch:
        with console_logger:
            console_logger.info("test message", batch=True)
        mock_batch.assert_called_once()


def test_console_logger_log_levels(console_logger):
    """Test all log levels."""
    with patch.object(console_logger.console, 'print') as mock_print:
        for level in LogLevel:
            method = getattr(console_logger, level.name.lower())
            method(f"{level.name} message")
            mock_print.assert_called()
            text = mock_print.call_args[0][0]
            assert level.name in str(text)
            mock_print.reset_mock()


def test_console_logger_indentation(console_logger):
    """Test log message indentation with context."""
    with patch.object(console_logger.console, 'print') as mock_print:
        console_logger.context.push("test_context")
        console_logger.info("indented message")
        
        text = mock_print.call_args[0][0]
        assert "  indented message" in str(text)  # Two spaces for one level
        
        console_logger.context.push("nested_context")
        console_logger.info("double indented message")
        
        text = mock_print.call_args[0][0]
        assert "    double indented message" in str(text)  # Four spaces for two levels 