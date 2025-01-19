"""Tests for system health monitoring."""

import os
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from nova.monitoring.system_health import DiskMetrics, MemoryMetrics, SystemHealthMonitor


@pytest.fixture
def temp_nova_dir():
    """Create a temporary Nova directory structure."""
    with tempfile.TemporaryDirectory() as temp_dir:
        nova_dir = Path(temp_dir)
        for subdir in ["vectors", "logs", "processing"]:
            (nova_dir / subdir).mkdir()
        yield nova_dir


@pytest.fixture
def mock_process():
    """Mock psutil.Process."""
    with patch("psutil.Process") as mock:
        process = Mock()
        process.memory_info.return_value = Mock(rss=104857600)  # 100MB in bytes
        process.cpu_percent.return_value = 25.0
        mock.return_value = process
        yield mock


@pytest.fixture
def mock_disk_usage():
    """Mock psutil.disk_usage."""
    with patch("psutil.disk_usage") as mock:
        mock.return_value = Mock(
            total=107374182400,  # 100GB in bytes
            used=32212254720,  # 30GB in bytes
            free=75161927680,  # 70GB in bytes
        )
        yield mock


def test_memory_metrics_status():
    """Test memory status thresholds."""
    # Healthy
    metrics = MemoryMetrics(current_mb=512, peak_mb=512)
    assert metrics.status == "healthy"

    # Warning
    metrics = MemoryMetrics(current_mb=1100, peak_mb=1100)
    assert metrics.status == "warning"

    # Critical
    metrics = MemoryMetrics(current_mb=1600, peak_mb=1600)
    assert metrics.status == "critical"


def test_disk_metrics_status():
    """Test disk status thresholds."""
    # Healthy
    metrics = DiskMetrics(total_gb=100, used_gb=50, free_gb=50)
    assert metrics.status == "healthy"
    assert metrics.used_percent == 50.0

    # Warning
    metrics = DiskMetrics(total_gb=100, used_gb=85, free_gb=15)
    assert metrics.status == "warning"
    assert metrics.used_percent == 85.0

    # Critical
    metrics = DiskMetrics(total_gb=100, used_gb=95, free_gb=5)
    assert metrics.status == "critical"
    assert metrics.used_percent == 95.0


def test_system_health_monitor_init(temp_nova_dir):
    """Test SystemHealthMonitor initialization."""
    monitor = SystemHealthMonitor(temp_nova_dir)
    assert monitor.base_path == temp_nova_dir
    assert monitor.required_dirs == ["vectors", "logs", "processing"]


def test_get_memory_metrics(mock_process):
    """Test memory metrics collection."""
    monitor = SystemHealthMonitor(Path("/tmp"))
    metrics = monitor.get_memory_metrics()

    assert metrics.current_mb == 100.0  # 100MB from mock
    assert metrics.peak_mb == 100.0
    assert metrics.status == "healthy"

    # Test peak memory tracking
    mock_process.return_value.memory_info.return_value = Mock(rss=209715200)  # 200MB
    metrics = monitor.get_memory_metrics()
    assert metrics.current_mb == 200.0
    assert metrics.peak_mb == 200.0


def test_get_cpu_percent(mock_process):
    """Test CPU usage collection."""
    monitor = SystemHealthMonitor(Path("/tmp"))
    assert monitor.get_cpu_percent() == 25.0


def test_get_disk_metrics(mock_disk_usage):
    """Test disk metrics collection."""
    monitor = SystemHealthMonitor(Path("/tmp"))
    metrics = monitor.get_disk_metrics()

    assert metrics.total_gb == 100.0
    assert metrics.used_gb == 30.0
    assert metrics.free_gb == 70.0
    assert metrics.used_percent == 30.0
    assert metrics.status == "healthy"


def test_check_directory_health(temp_nova_dir):
    """Test directory health checks."""
    monitor = SystemHealthMonitor(temp_nova_dir)
    health = monitor.check_directory_health()

    assert all(status == "healthy" for status in health.values())

    # Test missing directory
    (temp_nova_dir / "vectors").rmdir()
    health = monitor.check_directory_health()
    assert health["vectors"] == "missing"

    # Test permission error
    os.chmod(temp_nova_dir / "logs", 0o000)
    health = monitor.check_directory_health()
    assert health["logs"] == "permission_error"


def test_get_system_health(mock_process, mock_disk_usage, temp_nova_dir):
    """Test comprehensive system health check."""
    monitor = SystemHealthMonitor(temp_nova_dir)
    health = monitor.get_system_health()

    assert "timestamp" in health
    assert health["status"] == "healthy"
    assert health["memory"]["current_mb"] == 100.0
    assert health["memory"]["status"] == "healthy"
    assert health["disk"]["total_gb"] == 100.0
    assert health["disk"]["used_percent"] == 30.0
    assert health["disk"]["status"] == "healthy"
    assert health["cpu_percent"] == 25.0
    assert all(status == "healthy" for status in health["directories"].values())
