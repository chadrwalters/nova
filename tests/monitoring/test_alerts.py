"""Test alert functionality."""

from datetime import datetime, timedelta
import logging
from unittest.mock import Mock, patch
import pytest
from nova.monitoring.alerts import (
    AlertManager, AlertingConfig, EmailConfig,
    Alert, AlertSeverity
)

@pytest.fixture
def alert_manager():
    """Create test alert manager."""
    config = AlertingConfig(
        email_config=EmailConfig(
            smtp_server="test.smtp.com",
            smtp_port=587,
            username="test",
            password="test",
            from_addr="test@test.com",
            to_addrs=["alerts@test.com"]
        ),
        slack_webhook="https://hooks.slack.com/test"
    )
    return AlertManager(config)

def test_check_query_latency(alert_manager):
    """Test query latency checking."""
    # Test normal latency
    alert_manager.check_query_latency(0.5)
    assert not alert_manager.active_alerts

    # Test high latency
    alert_manager.check_query_latency(2.0)
    assert len(alert_manager.active_alerts) == 1
    alert = next(iter(alert_manager.active_alerts.values()))
    assert alert.severity == AlertSeverity.WARNING
    assert "latency" in alert.message.lower()

def test_check_error_rate(alert_manager):
    """Test error rate checking."""
    # Test normal error rate
    alert_manager.check_error_rate(1, 100)  # 1% error rate
    assert not alert_manager.active_alerts

    # Test high error rate
    alert_manager.check_error_rate(20, 100)  # 20% error rate
    assert len(alert_manager.active_alerts) == 1
    alert = next(iter(alert_manager.active_alerts.values()))
    assert alert.severity == AlertSeverity.ERROR
    assert "error rate" in alert.message.lower()

def test_check_memory_usage(alert_manager):
    """Test memory usage checking."""
    # Test normal memory usage
    alert_manager.check_memory_usage(2 * 1024 * 1024 * 1024)  # 2GB
    assert not alert_manager.active_alerts

    # Test high memory usage
    alert_manager.check_memory_usage(5 * 1024 * 1024 * 1024)  # 5GB
    assert len(alert_manager.active_alerts) == 1
    alert = next(iter(alert_manager.active_alerts.values()))
    assert alert.severity == AlertSeverity.WARNING
    assert "memory usage" in alert.message.lower()

def test_check_vector_store_size(alert_manager):
    """Test vector store size checking."""
    # Test normal size
    alert_manager.check_vector_store_size(500000)
    assert not alert_manager.active_alerts

    # Test large size
    alert_manager.check_vector_store_size(1500000)
    assert len(alert_manager.active_alerts) == 1
    alert = next(iter(alert_manager.active_alerts.values()))
    assert alert.severity == AlertSeverity.WARNING
    assert "vector store size" in alert.message.lower()

def test_check_rate_limits(alert_manager):
    """Test rate limit checking."""
    # Test normal rate limits
    alert_manager.check_rate_limits("test_service", 200)
    assert not alert_manager.active_alerts

    # Test low rate limits
    alert_manager.check_rate_limits("test_service", 50)
    assert len(alert_manager.active_alerts) == 1
    alert = next(iter(alert_manager.active_alerts.values()))
    assert alert.severity == AlertSeverity.WARNING
    assert "rate limits" in alert.message.lower()

def test_resolve_alert(alert_manager):
    """Test alert resolution."""
    # Create an alert
    alert_manager.check_query_latency(2.0)
    assert len(alert_manager.active_alerts) == 1
    alert_id = next(iter(alert_manager.active_alerts.keys()))

    # Resolve the alert
    alert_manager.resolve_alert(alert_id)
    assert not alert_manager.active_alerts

@patch('smtplib.SMTP')
def test_email_notification(mock_smtp, alert_manager):
    """Test email notification sending."""
    mock_server = Mock()
    mock_smtp.return_value.__enter__.return_value = mock_server

    alert = Alert(
        severity=AlertSeverity.WARNING,
        title="Test Alert",
        message="Test message",
        timestamp=datetime.now(),
        metric_name="test_metric",
        current_value=1.5,
        threshold_value=1.0
    )

    alert_manager._send_email_notification(alert)
    assert mock_server.send_message.called

@patch('requests.post')
def test_slack_notification(mock_post, alert_manager):
    """Test Slack notification sending."""
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_post.return_value = mock_response

    alert = Alert(
        severity=AlertSeverity.WARNING,
        title="Test Alert",
        message="Test message",
        timestamp=datetime.now(),
        metric_name="test_metric",
        current_value=1.5,
        threshold_value=1.0
    )

    alert_manager._send_slack_notification(alert)
    assert mock_post.called

@patch('logging.Logger.error')
def test_notification_error_handling(mock_logger, alert_manager):
    """Test error handling in notifications."""
    # Test email error handling
    with patch('smtplib.SMTP') as mock_smtp:
        mock_smtp.side_effect = Exception("SMTP error")
        alert = Alert(
            severity=AlertSeverity.WARNING,
            title="Test Alert",
            message="Test message",
            timestamp=datetime.now(),
            metric_name="test_metric",
            current_value=1.5,
            threshold_value=1.0
        )
        alert_manager._send_email_notification(alert)
        assert mock_logger.called

    # Test Slack error handling
    with patch('requests.post') as mock_post:
        mock_post.side_effect = Exception("Slack error")
        alert_manager._send_slack_notification(alert)
        assert mock_logger.called
