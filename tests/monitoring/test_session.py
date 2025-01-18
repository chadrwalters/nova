"""Tests for session monitoring functionality."""

import time
from datetime import datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from nova.monitoring.session import SessionMetrics, SessionMonitor


@pytest.fixture
def mock_process():
    """Create a mock psutil Process."""
    with patch("psutil.Process") as mock:
        process = MagicMock()
        process.memory_info.return_value.rss = 1024 * 1024 * 100  # 100 MB
        process.cpu_percent.return_value = 50.0
        process.memory_percent.return_value = 25.0
        mock.return_value = process
        yield mock


@pytest.fixture
def mock_disk_usage():
    """Create a mock psutil disk_usage."""
    with patch("psutil.disk_usage") as mock:
        disk = MagicMock()
        disk.percent = 45.0
        mock.return_value = disk
        yield mock


@pytest.fixture
def session_monitor(tmp_path: Path, mock_process, mock_disk_usage) -> SessionMonitor:
    """Create a session monitor instance."""
    monitor = SessionMonitor(tmp_path)
    # Create required directories
    (tmp_path / "vectors").mkdir(parents=True)
    (tmp_path / "processing").mkdir()
    (tmp_path / "logs").mkdir()
    return monitor


def test_session_metrics_initialization():
    """Test SessionMetrics initialization."""
    metrics = SessionMetrics(start_time=datetime.now())

    # Check base metrics
    assert metrics.queries_processed == 0
    assert metrics.total_query_time == 0.0
    assert metrics.peak_memory_mb == 0.0
    assert metrics.errors_encountered == 0
    assert metrics.last_error_time is None
    assert metrics.last_error_message is None

    # Check rebuild metrics
    assert metrics.rebuild_start_time is None
    assert metrics.rebuild_end_time is None
    assert metrics.chunks_processed == 0
    assert metrics.total_chunks == 0
    assert metrics.processing_time == 0.0
    assert metrics.rebuild_errors == 0
    assert metrics.rebuild_last_error_time is None
    assert metrics.rebuild_last_error_message is None
    assert metrics.rebuild_peak_memory_mb == 0.0


def test_track_rebuild_progress(session_monitor):
    """Test rebuild progress tracking initialization."""
    total_chunks = 100
    session_monitor.track_rebuild_progress(total_chunks)

    assert session_monitor.metrics.rebuild_start_time is not None
    assert session_monitor.metrics.rebuild_end_time is None
    assert session_monitor.metrics.chunks_processed == 0
    assert session_monitor.metrics.total_chunks == total_chunks
    assert session_monitor.metrics.processing_time == 0.0
    assert session_monitor.metrics.rebuild_errors == 0
    assert session_monitor.metrics.rebuild_last_error_time is None
    assert session_monitor.metrics.rebuild_last_error_message is None
    assert session_monitor.metrics.rebuild_peak_memory_mb == 0.0


def test_update_rebuild_progress(session_monitor):
    """Test rebuild progress updates."""
    session_monitor.track_rebuild_progress(100)

    # Update progress
    session_monitor.update_rebuild_progress(50, 30.5)

    assert session_monitor.metrics.chunks_processed == 50
    assert session_monitor.metrics.processing_time == 30.5
    assert session_monitor.metrics.rebuild_peak_memory_mb == 100.0  # From mock process


def test_record_rebuild_error(session_monitor):
    """Test rebuild error recording."""
    error_message = "Test rebuild error"
    session_monitor.record_rebuild_error(error_message)

    assert session_monitor.metrics.rebuild_errors == 1
    assert session_monitor.metrics.rebuild_last_error_time is not None
    assert session_monitor.metrics.rebuild_last_error_message == error_message


def test_complete_rebuild(session_monitor):
    """Test rebuild completion."""
    session_monitor.track_rebuild_progress(100)
    session_monitor.update_rebuild_progress(100, 60.0)
    session_monitor.complete_rebuild()

    assert session_monitor.metrics.rebuild_end_time is not None


def test_get_rebuild_stats_not_started(session_monitor):
    """Test getting rebuild stats when rebuild hasn't started."""
    stats = session_monitor.get_rebuild_stats()
    assert stats["status"] == "not_started"


def test_get_rebuild_stats_in_progress(session_monitor):
    """Test getting rebuild stats during rebuild."""
    session_monitor.track_rebuild_progress(100)
    session_monitor.update_rebuild_progress(50, 30.0)

    stats = session_monitor.get_rebuild_stats()

    assert stats["status"] == "in_progress"
    assert stats["progress"]["chunks_processed"] == 50
    assert stats["progress"]["total_chunks"] == 100
    assert stats["progress"]["percent_complete"] == 50.0
    assert "start_time" in stats["timing"]
    assert stats["timing"]["end_time"] is None
    assert stats["timing"]["processing_time"] == 30.0
    assert stats["performance"]["chunks_per_second"] > 0
    assert stats["performance"]["peak_memory_mb"] == 100.0  # From mock process
    assert stats["errors"]["count"] == 0


def test_get_rebuild_stats_completed(session_monitor):
    """Test getting rebuild stats after completion."""
    session_monitor.track_rebuild_progress(100)
    session_monitor.update_rebuild_progress(100, 60.0)
    time.sleep(0.1)  # Ensure some elapsed time
    session_monitor.complete_rebuild()

    stats = session_monitor.get_rebuild_stats()

    assert stats["status"] == "completed"
    assert stats["progress"]["chunks_processed"] == 100
    assert stats["progress"]["total_chunks"] == 100
    assert stats["progress"]["percent_complete"] == 100.0
    assert "start_time" in stats["timing"]
    assert stats["timing"]["end_time"] is not None
    assert stats["timing"]["processing_time"] == 60.0
    assert stats["performance"]["chunks_per_second"] > 0
    assert stats["performance"]["peak_memory_mb"] == 100.0  # From mock process
    assert stats["errors"]["count"] == 0
