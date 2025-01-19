"""Tests for health warning system."""

import tempfile
from collections.abc import Generator
from datetime import datetime
from pathlib import Path

import pytest

from nova.monitoring.warnings import (
    HealthWarningSystem,
    Warning,
    WarningCategory,
    WarningSeverity,
    WarningThresholds,
)


@pytest.fixture
def temp_nova_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


def test_warning_thresholds() -> None:
    """Test warning threshold configuration."""
    thresholds = WarningThresholds(
        memory_warning_mb=2048.0,
        memory_critical_mb=3072.0,
        disk_warning_percent=75.0,
        disk_critical_percent=85.0,
    )

    # Check custom values
    assert thresholds.memory_warning_mb == 2048.0
    assert thresholds.memory_critical_mb == 3072.0
    assert thresholds.disk_warning_percent == 75.0
    assert thresholds.disk_critical_percent == 85.0

    # Check defaults remain unchanged
    assert thresholds.cpu_warning_percent == 70.0
    assert thresholds.cpu_critical_percent == 85.0
    assert thresholds.max_vector_store_size_gb == 10.0


def test_warning_creation() -> None:
    """Test warning object creation and serialization."""
    now = datetime.now()
    warning = Warning(
        category=WarningCategory.MEMORY,
        severity=WarningSeverity.WARNING,
        message="High memory usage",
        timestamp=now,
        details={"current_mb": "1024", "threshold_mb": "1536"},
    )

    # Check warning attributes
    assert warning.category == WarningCategory.MEMORY
    assert warning.severity == WarningSeverity.WARNING
    assert warning.message == "High memory usage"
    assert warning.timestamp == now
    assert warning.details == {"current_mb": "1024", "threshold_mb": "1536"}
    assert not warning.resolved
    assert warning.resolved_at is None

    # Check dictionary conversion
    warning_dict = warning.to_dict()
    assert warning_dict["category"] == "memory"
    assert warning_dict["severity"] == "warning"
    assert warning_dict["message"] == "High memory usage"
    assert warning_dict["timestamp"] == now.isoformat()
    assert warning_dict["details"] == {"current_mb": "1024", "threshold_mb": "1536"}
    assert not warning_dict["resolved"]
    assert warning_dict["resolved_at"] is None


def test_warning_system_initialization(temp_nova_dir: Path) -> None:
    """Test warning system initialization."""
    # Test with default thresholds
    warning_system = HealthWarningSystem(temp_nova_dir)
    assert warning_system.thresholds.memory_warning_mb == 1024.0
    assert warning_system.warnings_file == temp_nova_dir / ".nova" / "warnings.json"
    assert len(warning_system.get_active_warnings()) == 0

    # Test with custom thresholds
    custom_thresholds = WarningThresholds(memory_warning_mb=2048.0)
    warning_system = HealthWarningSystem(temp_nova_dir, thresholds=custom_thresholds)
    assert warning_system.thresholds.memory_warning_mb == 2048.0


def test_warning_persistence(temp_nova_dir: Path) -> None:
    """Test warning persistence to disk."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Add some warnings
    warning_system.add_warning(
        category=WarningCategory.MEMORY,
        severity=WarningSeverity.WARNING,
        message="High memory usage",
        details={"current_mb": "1024"},
    )
    warning_system.add_warning(
        category=WarningCategory.DISK,
        severity=WarningSeverity.CRITICAL,
        message="Low disk space",
        details={"free_gb": "2.5"},
    )

    # Create new instance and verify loaded warnings
    new_system = HealthWarningSystem(temp_nova_dir)
    active_warnings = new_system.get_active_warnings()
    assert len(active_warnings) == 2

    memory_warning = next(w for w in active_warnings if w.category == WarningCategory.MEMORY)
    assert memory_warning.severity == WarningSeverity.WARNING
    assert memory_warning.message == "High memory usage"
    assert memory_warning.details == {"current_mb": "1024"}

    disk_warning = next(w for w in active_warnings if w.category == WarningCategory.DISK)
    assert disk_warning.severity == WarningSeverity.CRITICAL
    assert disk_warning.message == "Low disk space"
    assert disk_warning.details == {"free_gb": "2.5"}


def test_warning_resolution(temp_nova_dir: Path) -> None:
    """Test warning resolution."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Add a warning
    warning_system.add_warning(
        category=WarningCategory.MEMORY,
        severity=WarningSeverity.WARNING,
        message="High memory usage",
    )

    # Verify warning is active
    active_warnings = warning_system.get_active_warnings()
    assert len(active_warnings) == 1

    # Resolve warning
    warning_system.resolve_warning(
        category=WarningCategory.MEMORY,
        message="High memory usage",
    )

    # Verify warning is resolved
    active_warnings = warning_system.get_active_warnings()
    assert len(active_warnings) == 0

    # Check warning history
    history = warning_system.get_warning_history()
    assert len(history) == 1
    resolved_warning = history[0]
    assert resolved_warning.category == WarningCategory.MEMORY
    assert resolved_warning.resolved
    assert resolved_warning.resolved_at is not None


def test_warning_filtering(temp_nova_dir: Path) -> None:
    """Test warning filtering by category and severity."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Add various warnings
    warning_system.add_warning(
        category=WarningCategory.MEMORY,
        severity=WarningSeverity.WARNING,
        message="High memory usage",
    )
    warning_system.add_warning(
        category=WarningCategory.MEMORY,
        severity=WarningSeverity.CRITICAL,
        message="Critical memory usage",
    )
    warning_system.add_warning(
        category=WarningCategory.DISK,
        severity=WarningSeverity.WARNING,
        message="Low disk space",
    )

    # Filter by category
    memory_warnings = warning_system.get_active_warnings(category=WarningCategory.MEMORY)
    assert len(memory_warnings) == 2
    assert all(w.category == WarningCategory.MEMORY for w in memory_warnings)

    # Filter by severity
    warning_level = warning_system.get_active_warnings(severity=WarningSeverity.WARNING)
    assert len(warning_level) == 2
    assert all(w.severity == WarningSeverity.WARNING for w in warning_level)

    # Filter by both
    critical_memory = warning_system.get_active_warnings(
        category=WarningCategory.MEMORY,
        severity=WarningSeverity.CRITICAL,
    )
    assert len(critical_memory) == 1
    assert critical_memory[0].message == "Critical memory usage"


def test_warning_deduplication(temp_nova_dir: Path) -> None:
    """Test warning deduplication."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Add same warning multiple times
    for _ in range(3):
        warning_system.add_warning(
            category=WarningCategory.MEMORY,
            severity=WarningSeverity.WARNING,
            message="High memory usage",
        )

    # Verify only one warning is active
    active_warnings = warning_system.get_active_warnings()
    assert len(active_warnings) == 1

    # Resolve warning
    warning_system.resolve_warning(
        category=WarningCategory.MEMORY,
        message="High memory usage",
    )

    # Add same warning again
    warning_system.add_warning(
        category=WarningCategory.MEMORY,
        severity=WarningSeverity.WARNING,
        message="High memory usage",
    )

    # Verify warning can be re-added after resolution
    active_warnings = warning_system.get_active_warnings()
    assert len(active_warnings) == 1


def test_memory_warning_detection(temp_nova_dir: Path) -> None:
    """Test memory warning detection."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Test below warning threshold
    warning_system.check_memory_warnings(memory_mb=512.0, peak_mb=768.0)
    assert len(warning_system.get_active_warnings()) == 0

    # Test warning threshold
    warning_system.check_memory_warnings(memory_mb=1100.0, peak_mb=1200.0)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 0  # No warning yet (needs sustained usage)

    # Test critical threshold
    warning_system.check_memory_warnings(memory_mb=1600.0, peak_mb=1700.0)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 2  # Critical usage + Peak warning
    critical = next(w for w in warnings if w.severity == WarningSeverity.CRITICAL)
    assert critical.category == WarningCategory.MEMORY
    assert critical.message == "Critical memory usage detected"

    # Test warning resolution
    warning_system.check_memory_warnings(memory_mb=512.0, peak_mb=1700.0)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1  # Only peak warning remains
    assert warnings[0].message == "Peak memory threshold exceeded"


def test_disk_warning_detection(temp_nova_dir: Path) -> None:
    """Test disk warning detection."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Test below warning threshold
    warning_system.check_disk_warnings(used_percent=70.0, free_gb=10.0)
    assert len(warning_system.get_active_warnings()) == 0

    # Test warning threshold
    warning_system.check_disk_warnings(used_percent=85.0, free_gb=8.0)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1
    assert warnings[0].severity == WarningSeverity.WARNING
    assert warnings[0].message == "High disk usage"

    # Test critical threshold with low free space
    warning_system.check_disk_warnings(used_percent=95.0, free_gb=2.0)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 3  # Warning + Critical + Low free space
    assert any(
        w.message == "Critical disk usage" and w.severity == WarningSeverity.CRITICAL
        for w in warnings
    )
    assert any(
        w.message == "Low free disk space" and w.severity == WarningSeverity.CRITICAL
        for w in warnings
    )

    # Test warning resolution
    warning_system.check_disk_warnings(used_percent=70.0, free_gb=10.0)
    assert len(warning_system.get_active_warnings()) == 0


def test_cpu_warning_detection(temp_nova_dir: Path) -> None:
    """Test CPU warning detection."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Test below warning threshold
    warning_system.check_cpu_warnings(cpu_percent=50.0)
    assert len(warning_system.get_active_warnings()) == 0

    # Test warning threshold
    warning_system.check_cpu_warnings(cpu_percent=75.0)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1
    assert warnings[0].severity == WarningSeverity.WARNING
    assert warnings[0].message == "High CPU usage"

    # Test critical threshold (needs sustained usage)
    warning_system.check_cpu_warnings(cpu_percent=90.0)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1  # Still just warning until sustained
    assert warnings[0].severity == WarningSeverity.WARNING

    # Test warning resolution
    warning_system.check_cpu_warnings(cpu_percent=50.0)
    assert len(warning_system.get_active_warnings()) == 0


def test_directory_warning_detection(temp_nova_dir: Path) -> None:
    """Test directory warning detection."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Test healthy directories
    dir_status = {
        "vectors": "healthy",
        "logs": "healthy",
        "processing": "healthy",
    }
    warning_system.check_directory_warnings(dir_status)
    assert len(warning_system.get_active_warnings()) == 0

    # Test missing directory
    dir_status["vectors"] = "missing"
    warning_system.check_directory_warnings(dir_status)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1
    assert warnings[0].severity == WarningSeverity.CRITICAL
    assert warnings[0].message == "Required directory missing: vectors"

    # Test permission error
    dir_status["logs"] = "permission_error"
    warning_system.check_directory_warnings(dir_status)
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 2
    assert any(
        w.message == "Directory permission error: logs" and w.severity == WarningSeverity.WARNING
        for w in warnings
    )

    # Test warning resolution
    dir_status = {
        "vectors": "healthy",
        "logs": "healthy",
        "processing": "healthy",
    }
    warning_system.check_directory_warnings(dir_status)
    assert len(warning_system.get_active_warnings()) == 0


def test_vector_store_warning_detection(temp_nova_dir: Path) -> None:
    """Test vector store warning detection."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Test below warning thresholds
    warning_system.check_vector_store_warnings(
        store_size_gb=5.0,
        error_rate=1.0,
        avg_search_time_ms=50.0,
    )
    assert len(warning_system.get_active_warnings()) == 0

    # Test size warning
    warning_system.check_vector_store_warnings(
        store_size_gb=11.0,
        error_rate=1.0,
        avg_search_time_ms=50.0,
    )
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1
    assert warnings[0].message == "Vector store size limit approaching"

    # Test error rate warning (clears previous)
    warning_system.check_vector_store_warnings(
        store_size_gb=5.0,
        error_rate=6.0,
        avg_search_time_ms=50.0,
    )
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1
    assert warnings[0].message == "High vector store error rate"

    # Test performance warning (clears previous)
    warning_system.check_vector_store_warnings(
        store_size_gb=5.0,
        error_rate=1.0,
        avg_search_time_ms=150.0,
    )
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1
    assert warnings[0].message == "Vector store performance degradation"

    # Test multiple warnings
    warning_system.check_vector_store_warnings(
        store_size_gb=11.0,
        error_rate=6.0,
        avg_search_time_ms=50.0,
    )
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 2
    assert any(w.message == "Vector store size limit approaching" for w in warnings)
    assert any(w.message == "High vector store error rate" for w in warnings)


def test_metadata_warning_detection(temp_nova_dir: Path) -> None:
    """Test metadata warning detection."""
    warning_system = HealthWarningSystem(temp_nova_dir)

    # Test below warning thresholds
    warning_system.check_metadata_warnings(
        docs_without_tags=1,
        total_docs=10,
        invalid_dates=0,
    )
    assert len(warning_system.get_active_warnings()) == 0

    # Test missing tags warning
    warning_system.check_metadata_warnings(
        docs_without_tags=25,
        total_docs=100,
        invalid_dates=0,
    )
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 1
    assert warnings[0].message == "High number of documents without tags"

    # Test invalid dates warning (adds to existing)
    warning_system.check_metadata_warnings(
        docs_without_tags=25,
        total_docs=100,
        invalid_dates=15,
    )
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 2
    assert any(w.message == "High number of documents without tags" for w in warnings)
    assert any(w.message == "Documents with invalid dates detected" for w in warnings)

    # Test warning resolution
    warning_system.check_metadata_warnings(
        docs_without_tags=5,  # Below 20% threshold
        total_docs=100,
        invalid_dates=5,  # Below 10% threshold
    )
    warnings = warning_system.get_active_warnings()
    assert len(warnings) == 0
