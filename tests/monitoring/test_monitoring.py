"""Tests for monitoring modules."""

from datetime import datetime, timedelta

import pytest

from nova.monitoring.logs import LogManager


@pytest.fixture
def log_dir(tmp_path):
    """Create a temporary log directory."""
    log_dir = tmp_path / ".nova" / "logs"
    log_dir.mkdir(parents=True)
    return log_dir


@pytest.fixture
def log_manager(log_dir):
    """Create a log manager instance."""
    return LogManager(str(log_dir))


@pytest.fixture
def sample_logs(log_dir):
    """Create sample log files."""
    log_path = log_dir / "test.log"
    current_time = datetime.now()
    with log_path.open("w") as f:
        f.write(
            f'{current_time.strftime("%Y-%m-%d %H:%M:%S")} INFO test Test info message\n'
            f'{(current_time + timedelta(minutes=1)).strftime("%Y-%m-%d %H:%M:%S")} ERROR test Test error message\n'
            f'{(current_time + timedelta(minutes=2)).strftime("%Y-%m-%d %H:%M:%S")} WARNING test Test warning message\n'
        )
    return log_path


class TestLogManager:
    """Test log management functionality."""

    def test_initialization(self, log_manager, log_dir):
        """Test manager initialization."""
        assert log_dir.exists()

    def test_log_stats(self, log_manager, sample_logs):
        """Test log statistics."""
        stats = log_manager.get_stats()
        assert stats["total_files"] == 1
        assert stats["total_entries"] == 3
        assert stats["error_entries"] == 1
        assert stats["warning_entries"] == 1
        assert stats["info_entries"] == 1

    def test_tail_logs(self, log_manager, sample_logs):
        """Test retrieving the last n log entries."""
        entries = log_manager.tail_logs(n=3)
        assert len(entries) == 3
        assert entries[0]["level"] == "WARNING"
        assert entries[0]["message"] == "Test warning message"
        assert entries[0]["component"] == "test"
        assert entries[1]["level"] == "ERROR"
        assert entries[1]["message"] == "Test error message"
        assert entries[1]["component"] == "test"
        assert entries[2]["level"] == "INFO"
        assert entries[2]["message"] == "Test info message"
        assert entries[2]["component"] == "test"
