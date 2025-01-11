"""Tests for alert storage functionality."""

import pytest
from datetime import datetime, timedelta, timezone
from nova.monitoring.alert_storage import AlertStorage, AlertStatus, AlertSeverity, StoredAlert

@pytest.fixture
def alert_storage():
    """Create test alert storage."""
    return AlertStorage("sqlite:///:memory:")

def test_store_alert(alert_storage):
    """Test storing a new alert."""
    alert = alert_storage.store_alert(
        alert_id="test_alert_1",
        alert_type="memory_pressure",
        severity="critical",
        message="High memory usage",
        component="system",
        value=95.5,
        metadata={"threshold": 90}
    )
    
    assert alert.alert_id == "test_alert_1"
    assert alert.type == "memory_pressure"
    assert alert.severity == AlertSeverity.CRITICAL
    assert alert.message == "High memory usage"
    assert alert.component == "system"
    assert alert.value == 95.5
    assert alert.alert_metadata == {"threshold": 90}
    assert alert.status == AlertStatus.ACTIVE

def test_get_alert(alert_storage):
    """Test retrieving a stored alert."""
    stored = alert_storage.store_alert(
        alert_id="test_alert_2",
        alert_type="gpu_memory",
        severity="warning",
        message="GPU memory pressure",
        component="gpu0"
    )
    
    alert = alert_storage.get_alert("test_alert_2")
    assert alert is not None
    assert alert.alert_id == stored.alert_id
    assert alert.type == stored.type
    assert alert.severity == stored.severity
    assert alert.message == stored.message
    assert alert.component == stored.component

def test_get_nonexistent_alert(alert_storage):
    """Test retrieving a non-existent alert."""
    alert = alert_storage.get_alert("nonexistent")
    assert alert is None

def test_get_alerts_with_filters(alert_storage):
    """Test retrieving alerts with filters."""
    # Store some test alerts
    alert_storage.store_alert(
        alert_id="test_1",
        alert_type="memory",
        severity="critical",
        message="Alert 1",
        component="system"
    )
    alert_storage.store_alert(
        alert_id="test_2",
        alert_type="memory",
        severity="warning",
        message="Alert 2",
        component="system"
    )
    alert_storage.store_alert(
        alert_id="test_3",
        alert_type="gpu",
        severity="critical",
        message="Alert 3",
        component="gpu0"
    )
    
    # Test filtering by severity
    critical_alerts = alert_storage.get_alerts(severity="critical")
    assert len(critical_alerts) == 2
    assert all(a.severity == AlertSeverity.CRITICAL for a in critical_alerts)
    
    # Test filtering by component
    gpu_alerts = alert_storage.get_alerts(component="gpu0")
    assert len(gpu_alerts) == 1
    assert gpu_alerts[0].component == "gpu0"
    
    # Test filtering by status
    active_alerts = alert_storage.get_alerts(status="active")
    assert len(active_alerts) == 3
    assert all(a.status == AlertStatus.ACTIVE for a in active_alerts)

def test_update_alert_status(alert_storage):
    """Test updating alert status."""
    alert = alert_storage.store_alert(
        alert_id="test_status",
        alert_type="test",
        severity="warning",
        message="Test alert",
        component="test"
    )
    
    # Update to acknowledged
    success = alert_storage.update_alert_status("test_status", "acknowledged")
    assert success is True
    
    updated = alert_storage.get_alert("test_status")
    assert updated.status == AlertStatus.ACKNOWLEDGED
    assert updated.updated_at > updated.created_at

def test_update_nonexistent_alert_status(alert_storage):
    """Test updating status of non-existent alert."""
    success = alert_storage.update_alert_status("nonexistent", "acknowledged")
    assert success is False

def test_delete_old_alerts(alert_storage):
    """Test deleting old alerts."""
    # Store some alerts with different timestamps
    now = datetime.now(timezone.utc)
    old_time = now - timedelta(days=7)
    
    # Create an old alert
    alert_storage.store_alert(
        alert_id="old_alert",
        alert_type="test",
        severity="info",
        message="Old alert",
        component="test"
    )
    # Manually update its timestamp
    session = alert_storage.Session()
    old_alert = session.query(StoredAlert).filter_by(alert_id="old_alert").first()
    old_alert.created_at = old_time
    session.commit()
    session.close()
    
    # Create a new alert
    alert_storage.store_alert(
        alert_id="new_alert",
        alert_type="test",
        severity="info",
        message="New alert",
        component="test"
    )
    
    # Delete alerts older than 5 days
    deleted = alert_storage.delete_old_alerts(now - timedelta(days=5))
    assert deleted == 1
    
    # Verify only new alert remains
    remaining = alert_storage.get_alerts()
    assert len(remaining) == 1
    assert remaining[0].alert_id == "new_alert"

def test_alert_severity_enum():
    """Test alert severity enum."""
    assert AlertSeverity.CRITICAL.value == "critical"
    assert AlertSeverity.WARNING.value == "warning"
    assert AlertSeverity.INFO.value == "info"

def test_alert_status_enum():
    """Test alert status enum."""
    assert AlertStatus.ACTIVE.value == "active"
    assert AlertStatus.ACKNOWLEDGED.value == "acknowledged"
    assert AlertStatus.RESOLVED.value == "resolved" 