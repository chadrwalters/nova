"""Tests for alert aggregation functionality."""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import Mock
from nova.monitoring.alert_storage import AlertStorage, AlertStatus, AlertSeverity
from nova.monitoring.alert_aggregation import AlertAggregator, AlertGroup, AlertTrend

@pytest.fixture
def mock_alert_storage():
    """Create mock alert storage."""
    mock = Mock(spec=AlertStorage)
    return mock

@pytest.fixture
def alert_aggregator(mock_alert_storage):
    """Create alert aggregator instance."""
    return AlertAggregator(mock_alert_storage)

def create_mock_alert(
    alert_id: str,
    alert_type: str,
    severity: AlertSeverity,
    component: str,
    created_at: datetime,
    status: AlertStatus = AlertStatus.ACTIVE
):
    """Helper to create mock alerts."""
    return Mock(
        alert_id=alert_id,
        type=alert_type,
        severity=severity,
        component=component,
        created_at=created_at,
        status=status
    )

def test_group_alerts(alert_aggregator, mock_alert_storage):
    """Test alert grouping functionality."""
    now = datetime.now(timezone.utc)
    
    # Create test alerts
    alerts = [
        # Memory alerts for system component
        create_mock_alert(
            "mem_1", "memory_pressure", AlertSeverity.WARNING,
            "system", now - timedelta(minutes=45)
        ),
        create_mock_alert(
            "mem_2", "memory_pressure", AlertSeverity.CRITICAL,
            "system", now - timedelta(minutes=30)
        ),
        create_mock_alert(
            "mem_3", "memory_pressure", AlertSeverity.WARNING,
            "system", now - timedelta(minutes=15)
        ),
        
        # Memory alerts for GPU component
        create_mock_alert(
            "gpu_1", "memory_pressure", AlertSeverity.WARNING,
            "gpu0", now - timedelta(minutes=40)
        ),
        create_mock_alert(
            "gpu_2", "memory_pressure", AlertSeverity.WARNING,
            "gpu0", now - timedelta(minutes=20)
        ),
        
        # Single API alert
        create_mock_alert(
            "api_1", "api_error", AlertSeverity.WARNING,
            "api", now - timedelta(minutes=10)
        )
    ]
    
    mock_alert_storage.get_alerts.return_value = alerts
    
    # Test grouping
    groups = alert_aggregator.group_alerts(
        time_window=timedelta(hours=1),
        min_group_size=2
    )
    
    assert len(groups) == 2  # Two groups with 2+ alerts
    
    # Check system memory group
    sys_group = next(g for g in groups if g.component == "system")
    assert sys_group.alert_type == "memory_pressure"
    assert sys_group.severity == AlertSeverity.CRITICAL
    assert len(sys_group.alerts) == 3
    assert sys_group.count == 3
    assert "gpu0" in sys_group.related_components
    
    # Check GPU memory group
    gpu_group = next(g for g in groups if g.component == "gpu0")
    assert gpu_group.alert_type == "memory_pressure"
    assert gpu_group.severity == AlertSeverity.WARNING
    assert len(gpu_group.alerts) == 2
    assert gpu_group.count == 2
    assert "system" in gpu_group.related_components

def test_component_correlations(alert_aggregator, mock_alert_storage):
    """Test component correlation analysis."""
    now = datetime.now(timezone.utc)
    
    # Create test alerts with correlated components
    alerts = [
        # System alerts
        create_mock_alert(
            "sys_mem", "memory_pressure", AlertSeverity.WARNING,
            "system", now - timedelta(minutes=30)
        ),
        create_mock_alert(
            "sys_cpu", "cpu_pressure", AlertSeverity.WARNING,
            "system", now - timedelta(minutes=20)
        ),
        
        # GPU alerts with similar patterns
        create_mock_alert(
            "gpu_mem", "memory_pressure", AlertSeverity.WARNING,
            "gpu0", now - timedelta(minutes=25)
        ),
        create_mock_alert(
            "gpu_cpu", "cpu_pressure", AlertSeverity.WARNING,
            "gpu0", now - timedelta(minutes=15)
        ),
        
        # API alert with different pattern
        create_mock_alert(
            "api_err", "api_error", AlertSeverity.WARNING,
            "api", now - timedelta(minutes=10)
        )
    ]
    
    mock_alert_storage.get_alerts.return_value = alerts
    
    correlations = alert_aggregator.get_component_correlations(
        time_window=timedelta(hours=1),
        correlation_threshold=2
    )
    
    assert len(correlations) == 2
    assert "system" in correlations
    assert "gpu0" in correlations
    assert "gpu0" in correlations["system"]
    assert "system" in correlations["gpu0"]
    assert "api" not in correlations

def test_analyze_trends(alert_aggregator, mock_alert_storage):
    """Test alert trend analysis."""
    now = datetime.now(timezone.utc)
    
    # Create test alerts with increasing trend
    alerts = [
        # First half of window: 1 alert
        create_mock_alert(
            "mem_1", "memory_pressure", AlertSeverity.WARNING,
            "system", now - timedelta(minutes=45)
        ),
        # Second half of window: 2 alerts
        create_mock_alert(
            "mem_2", "memory_pressure", AlertSeverity.CRITICAL,
            "system", now - timedelta(minutes=15)
        ),
        create_mock_alert(
            "mem_3", "memory_pressure", AlertSeverity.WARNING,
            "system", now - timedelta(minutes=5)
        )
    ]
    
    mock_alert_storage.get_alerts.return_value = alerts
    
    trends = alert_aggregator.analyze_trends(
        time_windows=[timedelta(hours=1)]
    )
    
    assert len(trends) == 1
    hour_trends = trends[timedelta(hours=1)]
    assert len(hour_trends) == 1
    
    trend = hour_trends[0]
    assert trend.alert_type == "memory_pressure"
    assert trend.component == "system"
    assert trend.alert_count == 3
    assert trend.is_increasing is True
    assert trend.severity_counts["warning"] == 2
    assert trend.severity_counts["critical"] == 1
    assert trend.rate_of_change > 0  # Positive rate of change

def test_empty_alerts(alert_aggregator, mock_alert_storage):
    """Test behavior with no alerts."""
    mock_alert_storage.get_alerts.return_value = []
    
    groups = alert_aggregator.group_alerts()
    assert len(groups) == 0
    
    correlations = alert_aggregator.get_component_correlations()
    assert len(correlations) == 0
    
    trends = alert_aggregator.analyze_trends()
    assert all(len(t) == 0 for t in trends.values()) 