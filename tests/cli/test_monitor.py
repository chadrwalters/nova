"""Tests for monitor command."""

from unittest.mock import MagicMock, Mock, call

import pytest

from nova.cli.commands.monitor import MonitorCommand
from nova.monitoring.logs import LogManager
from nova.monitoring.session import SessionMonitor
from nova.vector_store.store import VectorStore


@pytest.fixture
def mock_vector_store() -> Mock:
    """Create a mock vector store."""
    return Mock(spec=VectorStore)


@pytest.fixture
def mock_log_manager() -> Mock:
    """Create a mock log manager."""
    return Mock(spec=LogManager)


@pytest.fixture
def mock_monitor(mock_vector_store: Mock, mock_log_manager: Mock) -> Mock:
    """Create a mock session monitor."""
    monitor = Mock(spec=SessionMonitor)
    monitor.vector_store = mock_vector_store
    monitor.log_manager = mock_log_manager
    return monitor


@pytest.fixture
def command(mock_vector_store: Mock, mock_monitor: Mock) -> MonitorCommand:
    """Create a monitor command instance."""
    return MonitorCommand(vector_store=mock_vector_store, monitor=mock_monitor)


def test_check_health(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test health check functionality."""
    # Setup mock health data
    mock_monitor.check_health.return_value = {
        "memory": {"status": "healthy"},
        "vector_store": "healthy",
        "monitor": "healthy",
        "logs": "healthy",
        "session_uptime": 123.45,
        "status": "healthy",
    }

    # Run health check
    command.check_health()

    # Verify monitor was called
    assert mock_monitor.check_health.call_count == 1


def test_show_stats(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test statistics display functionality."""
    # Setup mock stats data
    mock_monitor.get_stats.return_value = {
        "memory": {
            "process": {"current_memory_mb": 100.5, "peak_memory_mb": 150.2, "warning_count": 0}
        },
        "session": {"start_time": "2024-01-01 12:00:00", "uptime": 3600.5},
        "profiles": [
            {"name": "test_profile", "timestamp": "2024-01-01 12:30:00", "duration": 30.5}
        ],
        "vector_store": {"total_chunks": 1000, "total_documents": 50},
        "monitor": {"active_sessions": 1},
        "logs": {"total_entries": 500},
    }

    # Run stats display
    command.show_stats()

    # Verify monitor was called
    assert mock_monitor.get_stats.call_count == 1


def test_show_logs(command: MonitorCommand, mock_monitor: Mock, mock_log_manager: Mock) -> None:
    """Test log display functionality."""
    # Setup mock log data
    mock_log_manager.tail_logs.return_value = [
        {
            "timestamp": "2024-01-01 12:00:00",
            "level": "INFO",
            "component": "test",
            "message": "Test message",
        },
        {
            "timestamp": "2024-01-01 12:01:00",
            "level": "ERROR",
            "component": "test",
            "message": "Error message",
        },
    ]

    # Run log display
    command.show_logs()

    # Verify log manager was called
    assert mock_log_manager.tail_logs.call_count == 1
    assert mock_log_manager.tail_logs.call_args == call(n=10)


def test_show_profiles(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test profile display functionality."""
    # Setup mock profile data
    mock_monitor.get_profiles.return_value = [
        {
            "name": "test_profile",
            "timestamp": "2024-01-01 12:00:00",
            "duration": 30.5,
            "stats_file": "stats.json",
            "profile_file": "profile.prof",
        }
    ]

    # Run profile display
    command.show_profiles()

    # Verify monitor was called
    assert mock_monitor.get_profiles.call_count == 1


def test_start_profile(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test profile creation functionality."""
    # Setup mock profile context
    mock_context = MagicMock()
    mock_monitor.start_profile.return_value = mock_context

    # Run profile creation
    command.start_profile("test_profile")

    # Verify monitor was called
    assert mock_monitor.start_profile.call_count == 1
    assert mock_monitor.start_profile.call_args == call("test_profile")


def test_invalid_subcommand(command: MonitorCommand) -> None:
    """Test handling of invalid subcommands."""
    with pytest.raises(SystemExit):
        command.run(subcommand="invalid")


def test_missing_profile_name(command: MonitorCommand) -> None:
    """Test handling of missing profile name."""
    command.start_profile("")
    # Should log error but not raise exception


def test_unavailable_log_manager(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test handling of unavailable log manager."""
    mock_monitor.log_manager = None
    command.show_logs()
    # Should log error but not raise exception


def test_empty_profiles(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test handling of empty profiles list."""
    mock_monitor.get_profiles.return_value = []
    command.show_profiles()
    # Should log info message but not raise exception


def test_health_check_error_handling(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test health check error handling."""
    # Setup mock to raise exception
    mock_monitor.check_health.side_effect = Exception("Test error")

    with pytest.raises(Exception):
        command.check_health()


def test_stats_error_handling(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test statistics error handling."""
    # Setup mock to raise exception
    mock_monitor.get_stats.side_effect = Exception("Test error")

    with pytest.raises(Exception):
        command.show_stats()


def test_logs_error_handling(
    command: MonitorCommand, mock_monitor: Mock, mock_log_manager: Mock
) -> None:
    """Test log display error handling."""
    # Setup mock to raise exception
    mock_log_manager.tail_logs.side_effect = Exception("Test error")

    with pytest.raises(Exception):
        command.show_logs()


def test_profiles_error_handling(command: MonitorCommand, mock_monitor: Mock) -> None:
    """Test profile display error handling."""
    # Setup mock to raise exception
    mock_monitor.get_profiles.side_effect = Exception("Test error")

    with pytest.raises(Exception):
        command.show_profiles()
