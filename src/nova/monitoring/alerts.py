"""Alert configuration and management."""

from dataclasses import asdict, dataclass, field
from datetime import datetime
import logging
import os
import smtplib
from email.message import EmailMessage
import requests
from typing import Dict, Optional, Any, List
import json
from pathlib import Path
from enum import Enum

from nova.monitoring.alert_types import (
    Alert, AlertGroup, AlertTrend,
    AlertSeverity, AlertStatus
)

class AlertJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for alert-related objects."""

    def default(self, obj):
        if isinstance(obj, Alert):
            return {
                "alert_id": obj.alert_id,
                "type": obj.type,
                "severity": obj.severity.value.upper() if isinstance(obj.severity, AlertSeverity) else str(obj.severity).upper(),
                "message": obj.message,
                "component": obj.component,
                "created_at": obj.created_at.isoformat() if isinstance(obj.created_at, datetime) else obj.created_at,
                "status": obj.status.value.upper() if isinstance(obj.status, AlertStatus) else str(obj.status).upper(),
                "alert_metadata": obj.alert_metadata
            }
        elif isinstance(obj, AlertGroup):
            return {
                "group_id": obj.group_id,
                "alert_type": obj.alert_type,
                "component": obj.component,
                "severity": obj.severity.value.upper() if isinstance(obj.severity, AlertSeverity) else str(obj.severity).upper(),
                "alerts": obj.alerts,
                "first_seen": obj.first_seen.isoformat() if isinstance(obj.first_seen, datetime) else obj.first_seen,
                "last_seen": obj.last_seen.isoformat() if isinstance(obj.last_seen, datetime) else obj.last_seen,
                "total_alerts": obj.total_alerts,
                "active_alerts": obj.active_alerts,
                "related_components": list(obj.related_components) if isinstance(obj.related_components, set) else obj.related_components
            }
        elif isinstance(obj, AlertTrend):
            return {
                "trend_id": obj.trend_id,
                "alert_type": obj.alert_type,
                "component": obj.component,
                "severity": obj.severity.value.upper() if isinstance(obj.severity, AlertSeverity) else str(obj.severity).upper(),
                "start_time": obj.start_time.isoformat() if isinstance(obj.start_time, datetime) else obj.start_time,
                "end_time": obj.end_time.isoformat() if isinstance(obj.end_time, datetime) else obj.end_time,
                "alert_count": obj.alert_count,
                "rate_of_change": obj.rate_of_change,
                "is_increasing": obj.is_increasing
            }
        elif isinstance(obj, (AlertSeverity, AlertStatus)):
            return obj.value.upper()
        elif isinstance(obj, datetime):
            return obj.isoformat()
        elif isinstance(obj, set):
            return list(obj)
        return super().default(obj)

def alert_json_dumps(obj: Any) -> str:
    """Dump an object to JSON string using AlertJSONEncoder."""
    return json.dumps(obj, cls=AlertJSONEncoder)

@dataclass
class EmailConfig:
    """Email configuration."""
    smtp_server: str = "smtp.gmail.com"
    smtp_port: int = 587
    username: str = ""
    password: str = ""
    from_addr: str = ""
    to_addrs: List[str] = field(default_factory=list)

@dataclass
class AlertingConfig:
    """Alert configuration."""
    max_query_latency: float = 1.0  # Maximum acceptable query latency in seconds
    max_error_rate: float = 0.01  # Maximum acceptable error rate (1%)
    max_memory_usage: int = 4 * 1024 * 1024 * 1024  # Maximum memory usage (4GB)
    max_vector_store_size: int = 1000000  # Maximum number of vectors in store
    min_rate_limit_remaining: int = 100  # Minimum remaining API calls before warning
    rate_limit_warning_threshold: float = 0.2  # Warn when remaining calls below 20%
    log_path: str = "logs/alerts.log"  # Path to alert log file
    email_config: Optional[EmailConfig] = None  # Email notification configuration
    slack_webhook: Optional[str] = None  # Slack webhook URL for notifications

class AlertManager:
    """Manager for monitoring alerts."""

    def __init__(self, config: AlertingConfig):
        """Initialize alert manager.

        Args:
            config: Alert configuration.
        """
        self.config = config
        self.active_alerts: Dict[str, Alert] = {}

        # Set up logging
        os.makedirs(os.path.dirname(config.log_path), exist_ok=True)
        self.logger = logging.getLogger("nova.alerts")
        handler = logging.FileHandler(config.log_path)
        handler.setFormatter(logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        ))
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)

    def check_query_latency(self, latency: float) -> None:
        """Check if query latency exceeds threshold.

        Args:
            latency: Query latency in seconds.
        """
        if latency > self.config.max_query_latency:
            alert_id = f"high_latency_{datetime.now().date()}"
            if alert_id not in self.active_alerts:
                alert = Alert(
                    severity=AlertSeverity.WARNING,
                    title="High Query Latency",
                    message=f"Query latency of {latency:.2f}s exceeds threshold of {self.config.max_query_latency}s",
                    timestamp=datetime.now(),
                    metric_name="query_latency",
                    current_value=latency,
                    threshold_value=self.config.max_query_latency
                )
                self._notify_alert(alert_id, alert)
                self.active_alerts[alert_id] = alert

    def check_error_rate(self, error_count: int, total_count: int) -> None:
        """Check if error rate exceeds threshold.

        Args:
            error_count: Number of errors
            total_count: Total number of requests
        """
        if total_count == 0:
            return

        error_rate = error_count / total_count
        if error_rate > self.config.max_error_rate:
            alert = Alert(
                title="High Error Rate",
                message=f"Error rate of {error_rate:.1%} exceeds maximum of {self.config.max_error_rate:.1%}",
                severity=AlertSeverity.ERROR
            )
            self._notify_alert("high_error_rate", alert)

    def check_memory_usage(self, memory_bytes: int) -> None:
        """Check if memory usage exceeds threshold."""
        if memory_bytes > self.config.max_memory_usage:
            alert_id = f"memory_usage_{datetime.now().date()}"
            if alert_id not in self.active_alerts:
                alert = Alert(
                    severity=AlertSeverity.WARNING,
                    title="High Memory Usage",
                    message=f"Memory usage ({memory_bytes / (1024*1024*1024):.2f}GB) exceeds threshold ({self.config.max_memory_usage / (1024*1024*1024):.2f}GB)",
                    timestamp=datetime.now(),
                    metric_name="memory_usage",
                    current_value=memory_bytes / (1024 * 1024 * 1024),
                    threshold_value=self.config.max_memory_usage / (1024 * 1024 * 1024)
                )
                self._notify_alert(alert_id, alert)
                self.active_alerts[alert_id] = alert

    def check_vector_store_size(self, size: int) -> None:
        """Check if vector store size exceeds threshold."""
        if size > self.config.max_vector_store_size:
            alert_id = f"vector_store_size_{datetime.now().date()}"
            if alert_id not in self.active_alerts:
                alert = Alert(
                    severity=AlertSeverity.WARNING,
                    title="Vector Store Size Exceeded",
                    message=f"Vector store size ({size}) exceeds threshold ({self.config.max_vector_store_size})",
                    timestamp=datetime.now(),
                    metric_name="vector_store_size",
                    current_value=float(size),
                    threshold_value=float(self.config.max_vector_store_size)
                )
                self._notify_alert(alert_id, alert)
                self.active_alerts[alert_id] = alert

    def check_rate_limits(self, service_name: str, remaining_calls: int) -> None:
        """Check API rate limits for a service.

        Args:
            service_name: Name of the service to check.
            remaining_calls: Number of API calls remaining.
        """
        if remaining_calls < self.config.min_rate_limit_remaining:
            alert_id = f"low_rate_limit_{service_name}_{datetime.now().date()}"
            if alert_id not in self.active_alerts:
                alert = Alert(
                    severity=AlertSeverity.WARNING,
                    title=f"Low Rate Limits for {service_name}",
                    message=f"Rate limits low: {remaining_calls} API calls remaining (threshold: {self.config.min_rate_limit_remaining})",
                    timestamp=datetime.now(),
                    metric_name="rate_limits_remaining",
                    current_value=float(remaining_calls),
                    threshold_value=float(self.config.min_rate_limit_remaining)
                )
                self._notify_alert(alert_id, alert)
                self.active_alerts[alert_id] = alert

    def resolve_alert(self, alert_id: str) -> None:
        """Resolve an active alert."""
        if alert_id in self.active_alerts:
            alert = self.active_alerts[alert_id]
            alert.resolved = True
            alert.resolved_at = datetime.now()
            self._notify_resolution(alert_id, alert)
            del self.active_alerts[alert_id]

    def _notify_alert(self, alert_id: str, alert: Alert) -> None:
        """Notify about a new alert.

        Args:
            alert_id: Unique identifier for the alert.
            alert: Alert object.
        """
        # Log the alert
        self.logger.warning(f"Alert: {alert.title} - {alert.message}")

        # Send notifications
        self._send_email_notification(alert)
        self._send_slack_notification(alert)

        # Store the alert
        self.active_alerts[alert_id] = alert

    def _notify_resolution(self, alert_id: str, alert: Alert) -> None:
        """Send alert resolution notifications."""
        # Log resolution
        self.logger.info(f"Resolved: {alert.message}")

        # Send email notification
        if self.config.email_config:
            try:
                msg = EmailMessage()
                msg.set_content(f"""
                Alert Resolved: {alert.severity.value}
                Title: {alert.title}
                Time: {alert.resolved_at}
                Metric: {alert.metric_name}
                Message: {alert.message}
                Duration: {alert.resolved_at - alert.timestamp}
                """)

                msg["Subject"] = f"Nova Alert Resolved: {alert.severity.value} - {alert.title}"
                msg["From"] = self.config.email_config.from_addr
                msg["To"] = ", ".join(self.config.email_config.to_addrs or [])

                with smtplib.SMTP(self.config.email_config.smtp_server, self.config.email_config.smtp_port) as server:
                    server.starttls()
                    server.login(self.config.email_config.username, self.config.email_config.password)
                    server.send_message(msg)
            except Exception as e:
                self.logger.error(f"Failed to send email resolution notification: {e}")

        # Send Slack notification
        if self.config.slack_webhook:
            try:
                payload = {
                    "attachments": [{
                        "color": self._get_slack_color(alert.severity),
                        "title": f"Alert Resolved: {alert.title}",
                        "text": alert.message,
                        "fields": [
                            {
                                "title": "Severity",
                                "value": alert.severity.value,
                                "short": True
                            },
                            {
                                "title": "Duration",
                                "value": str(alert.resolved_at - alert.timestamp),
                                "short": True
                            }
                        ],
                        "ts": int(alert.resolved_at.timestamp())
                    }]
                }
                requests.post(self.config.slack_webhook, json=payload)
            except Exception as e:
                self.logger.error(f"Failed to send Slack resolution notification: {e}")

    def _send_email_notification(self, alert: Alert) -> None:
        """Send email notification for an alert."""
        if not self.config.email_config:
            return

        try:
            msg = EmailMessage()
            msg.set_content(f"""
            Alert: {alert.severity.value}
            Title: {alert.title}
            Time: {alert.timestamp}
            Metric: {alert.metric_name}
            Current Value: {alert.current_value}
            Threshold: {alert.threshold_value}
            Message: {alert.message}
            """)

            msg["Subject"] = f"Nova Alert: {alert.severity.value} - {alert.title}"
            msg["From"] = self.config.email_config.from_addr
            msg["To"] = ", ".join(self.config.email_config.to_addrs or [])

            with smtplib.SMTP(self.config.email_config.smtp_server, self.config.email_config.smtp_port) as server:
                server.starttls()
                server.login(self.config.email_config.username, self.config.email_config.password)
                server.send_message(msg)
        except Exception as e:
            self.logger.error(f"Failed to send email notification: {e}")

    def _send_slack_notification(self, alert: Alert) -> None:
        """Send Slack notification for an alert."""
        if not self.config.slack_webhook:
            return

        try:
            payload = {
                "attachments": [{
                    "color": self._get_slack_color(alert.severity),
                    "title": f"Nova Alert: {alert.title}",
                    "text": alert.message,
                    "fields": [
                        {
                            "title": "Severity",
                            "value": alert.severity.value,
                            "short": True
                        },
                        {
                            "title": "Metric",
                            "value": alert.metric_name,
                            "short": True
                        },
                        {
                            "title": "Value",
                            "value": str(alert.current_value),
                            "short": True
                        },
                        {
                            "title": "Threshold",
                            "value": str(alert.threshold_value),
                            "short": True
                        },
                        {
                            "title": "Time",
                            "value": str(alert.timestamp),
                            "short": True
                        }
                    ]
                }]
            }
            requests.post(self.config.slack_webhook, json=payload)
        except Exception as e:
            self.logger.error(f"Failed to send Slack notification: {e}")

    def _get_slack_color(self, severity: AlertSeverity) -> str:
        """Get Slack color for alert severity."""
        return {
            AlertSeverity.INFO: "#36a64f",  # Green
            AlertSeverity.WARNING: "#ffcc00",  # Yellow
            AlertSeverity.ERROR: "#ff9900",  # Orange
            AlertSeverity.CRITICAL: "#ff0000"  # Red
        }.get(severity, "#cccccc")  # Gray default
