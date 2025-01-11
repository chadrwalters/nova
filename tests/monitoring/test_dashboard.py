"""Tests for monitoring dashboard endpoints."""

from datetime import datetime, timezone, timedelta
from unittest.mock import Mock, patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from nova.monitoring.alert_storage import AlertStatus, AlertSeverity
from nova.monitoring.alert_aggregation import AlertGroup, AlertTrend
from nova.monitoring.dashboard import DashboardAPI, Alert

@pytest.fixture
def mock_alert_storage():
    """Create a mock alert storage instance."""
    return Mock()

@pytest.fixture
def mock_alert_aggregator():
    """Create a mock alert aggregator instance."""
    return Mock()

@pytest.fixture
def mock_alert_manager():
    """Create a mock alert manager instance."""
    return Mock()

@pytest.fixture
def mock_memory_monitor():
    """Create a mock memory monitor instance."""
    return Mock()

@pytest.fixture
def app():
    """Create FastAPI app instance."""
    return FastAPI()

@pytest.fixture
def dashboard_api(app, mock_alert_manager, mock_memory_monitor, mock_alert_storage, mock_alert_aggregator):
    """Create a dashboard API instance with mocked dependencies."""
    api = DashboardAPI(app, mock_alert_manager, mock_memory_monitor)
    api.alert_storage = mock_alert_storage
    api.alert_aggregator = mock_alert_aggregator
    return api

@pytest.fixture
def client(dashboard_api):
    """Create a test client."""
    from fastapi import FastAPI
    app = FastAPI()
    app.include_router(dashboard_api.router)
    return TestClient(app)

def test_get_current_alerts(client, dashboard_api, mock_alert_storage):
    """Test getting current alerts."""
    mock_alerts = [
        Alert(
            alert_id="test_1",
            type="memory_pressure",
            severity=AlertSeverity.CRITICAL,
            message="High memory usage",
            component="system",
            created_at=datetime.now(timezone.utc),
            status=AlertStatus.ACTIVE,
            alert_metadata={"threshold": 90}
        )
    ]
    mock_alert_storage.get_current_alerts.return_value = mock_alerts

    response = client.get("/api/alerts/current")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    alert = data[0]
    assert alert["alert_id"] == "test_1"
    assert alert["type"] == "memory_pressure"
    assert alert["severity"] == "CRITICAL"
    assert alert["status"] == "ACTIVE"

def test_get_alert_history(client, dashboard_api, mock_alert_storage):
    """Test getting alert history."""
    mock_alerts = [
        Alert(
            alert_id="test_1",
            type="memory_pressure",
            severity=AlertSeverity.CRITICAL,
            message="High memory usage",
            component="system",
            created_at=datetime.now(timezone.utc),
            status=AlertStatus.RESOLVED,
            alert_metadata={"threshold": 90}
        )
    ]
    mock_alert_storage.get_alert_history.return_value = mock_alerts

    response = client.get("/api/alerts/history")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    alert = data[0]
    assert alert["alert_id"] == "test_1"
    assert alert["type"] == "memory_pressure"
    assert alert["severity"] == "CRITICAL"
    assert alert["status"] == "RESOLVED"

def test_get_alert_summary(client, dashboard_api, mock_alert_storage):
    """Test getting alert summary."""
    mock_summary = {
        "total_alerts": 2,
        "active_alerts": 1,
        "acknowledged_alerts": 1,
        "resolved_alerts": 0
    }
    mock_alert_storage.get_alert_summary.return_value = mock_summary

    response = client.get("/api/alerts/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["total_alerts"] == 2
    assert data["active_alerts"] == 1
    assert data["acknowledged_alerts"] == 1
    assert data["resolved_alerts"] == 0

def test_acknowledge_alert(client, dashboard_api, mock_alert_storage):
    """Test acknowledging an alert."""
    mock_alert_storage.update_alert_status.return_value = True

    response = client.post("/api/alerts/test_1/acknowledge")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Alert acknowledged successfully"

def test_resolve_alert(client, dashboard_api, mock_alert_storage):
    """Test resolving an alert."""
    mock_alert_storage.update_alert_status.return_value = True

    response = client.post("/api/alerts/test_1/resolve")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert data["message"] == "Alert resolved successfully"

def test_get_memory_summary(client, dashboard_api, mock_memory_monitor):
    """Test getting memory summary."""
    mock_memory_monitor.total_memory = 16000000000
    mock_memory_monitor.used_memory = 8000000000
    mock_memory_monitor.available_memory = 8000000000
    mock_memory_monitor.memory_pressure = False

    response = client.get("/api/memory/summary")
    assert response.status_code == 200

    data = response.json()
    assert data["total"] == 16000000000
    assert data["used"] == 8000000000
    assert data["available"] == 8000000000
    assert data["pressure"] is False

def test_get_memory_pressure(client, dashboard_api, mock_memory_monitor):
    """Test getting memory pressure status."""
    mock_memory_monitor.memory_pressure = True

    response = client.get("/api/memory/pressure")
    assert response.status_code == 200

    data = response.json()
    assert data["memory_pressure"] is True

def test_get_index_memory(client, dashboard_api, mock_memory_monitor):
    """Test getting index memory usage."""
    mock_data = {
        "index1": 1000000,
        "index2": 2000000
    }
    mock_memory_monitor.get_index_memory.return_value = mock_data

    response = client.get("/api/memory/indices")
    assert response.status_code == 200

    data = response.json()
    assert data == mock_data

def test_get_vectorstore_metrics(client, dashboard_api):
    """Test getting vector store metrics."""
    response = client.get("/api/vectorstore/metrics")
    assert response.status_code == 200

def test_get_vectorstore_performance(client, dashboard_api):
    """Test getting vector store performance metrics."""
    response = client.get("/api/vectorstore/performance")
    assert response.status_code == 200

def test_get_rate_limits(client, dashboard_api):
    """Test getting rate limit status."""
    response = client.get("/api/rate_limits")
    assert response.status_code == 200

def test_get_service_errors(client, dashboard_api):
    """Test getting service error metrics."""
    response = client.get("/api/errors")
    assert response.status_code == 200

def test_error_handling(client, dashboard_api, mock_memory_monitor):
    """Test error handling."""
    # Simulate an error in memory monitor
    mock_memory_monitor.total_memory = None
    mock_memory_monitor.used_memory = None
    mock_memory_monitor.available_memory = None
    mock_memory_monitor.memory_pressure = None

    response = client.get("/api/memory/summary")
    assert response.status_code == 500

    data = response.json()
    assert "detail" in data
    assert "Failed to get memory summary" in data["detail"]

def test_error_handling_with_exception(client, dashboard_api, mock_memory_monitor):
    """Test error handling with a specific exception."""
    def raise_error():
        raise ValueError("Memory monitor error")

    mock_memory_monitor.get_index_memory.side_effect = raise_error

    response = client.get("/api/memory/indices")
    assert response.status_code == 500

    data = response.json()
    assert "detail" in data
    assert "Failed to get index memory usage" in data["detail"]

def test_get_alert_groups(client, dashboard_api, mock_alert_aggregator):
    """Test getting alert groups."""
    now = datetime.now(timezone.utc)
    alerts = [
        Alert(
            alert_id="test_1",
            type="memory_pressure",
            severity=AlertSeverity.CRITICAL,
            message="High memory usage",
            component="system",
            created_at=now,
            status=AlertStatus.ACTIVE,
            alert_metadata={"threshold": 90}
        ),
        Alert(
            alert_id="test_2",
            type="memory_pressure",
            severity=AlertSeverity.CRITICAL,
            message="High memory usage",
            component="system",
            created_at=now + timedelta(minutes=5),
            status=AlertStatus.ACTIVE,
            alert_metadata={"threshold": 90}
        )
    ]

    mock_groups = [
        AlertGroup(
            group_id="memory_system_123",
            alert_type="memory_pressure",
            component="system",
            severity=AlertSeverity.CRITICAL,
            alerts=alerts,
            first_seen=now,
            last_seen=now + timedelta(minutes=5),
            total_alerts=2,
            active_alerts=2
        )
    ]
    mock_alert_aggregator.get_alert_groups.return_value = mock_groups

    response = client.get("/api/alerts/groups")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    group = data[0]
    assert group["group_id"] == "memory_system_123"
    assert group["alert_type"] == "memory_pressure"
    assert group["component"] == "system"
    assert group["severity"] == "CRITICAL"
    assert len(group["alerts"]) == 2
    assert group["total_alerts"] == 2
    assert group["active_alerts"] == 2

def test_get_component_correlations(client, dashboard_api, mock_alert_aggregator):
    """Test getting component correlations."""
    # Mock correlations
    correlations = {
        "system": {"gpu0", "gpu1"},
        "gpu0": {"system", "gpu1"},
        "gpu1": {"system", "gpu0"}
    }

    mock_alert_aggregator.get_component_correlations.return_value = correlations

    response = client.get("/api/alerts/correlations")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 3
    assert set(data["system"]) == {"gpu0", "gpu1"}
    assert set(data["gpu0"]) == {"system", "gpu1"}
    assert set(data["gpu1"]) == {"system", "gpu0"}

def test_get_alert_trends(client, dashboard_api, mock_alert_aggregator):
    """Test getting alert trends."""
    now = datetime.now(timezone.utc)
    mock_trends = [
        AlertTrend(
            trend_id="memory_system_trend",
            alert_type="memory_pressure",
            component="system",
            severity=AlertSeverity.CRITICAL,
            start_time=now - timedelta(hours=1),
            end_time=now,
            alert_count=10,
            rate_of_change=1.5,
            is_increasing=True
        )
    ]
    mock_alert_aggregator.get_alert_trends.return_value = mock_trends

    response = client.get("/api/alerts/trends")
    assert response.status_code == 200

    data = response.json()
    assert len(data) == 1
    trend = data[0]
    assert trend["trend_id"] == "memory_system_trend"
    assert trend["alert_type"] == "memory_pressure"
    assert trend["component"] == "system"
    assert trend["severity"] == "CRITICAL"
    assert trend["alert_count"] == 10
    assert trend["rate_of_change"] == 1.5
    assert trend["is_increasing"] is True
