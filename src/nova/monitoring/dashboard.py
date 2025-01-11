"""Dashboard endpoints for Nova monitoring."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
import logging
from fastapi import FastAPI, HTTPException, Query, APIRouter, Response, Request
from prometheus_client import REGISTRY

from .alerts import AlertManager
from .memory import MemoryMonitor
from .alert_storage import AlertStorage, AlertStatus, AlertSeverity
from .alert_aggregation import AlertAggregator, AlertGroup, AlertTrend
from .cache import cached_response
from .metrics import (
    MEMORY_PRESSURE_ALERTS,
    API_ERRORS,
    QUERY_ERRORS,
    RATE_LIMITS_REMAINING,
    VECTOR_STORE_SIZE,
    VECTOR_STORE_MEMORY
)

logger = logging.getLogger(__name__)

@dataclass
class Alert:
    """Alert information."""
    alert_id: str
    type: str
    severity: str
    message: str
    component: str
    created_at: datetime
    status: str
    alert_metadata: Optional[Dict] = None

@dataclass
class AlertSummary:
    """Summary of alerts."""
    total_alerts: int
    active_alerts: int
    acknowledged_alerts: int
    resolved_alerts: int

class DashboardAPI:
    """API endpoints for monitoring dashboard."""

    def __init__(self, app: FastAPI, alert_manager: AlertManager, memory_monitor: MemoryMonitor):
        """Initialize dashboard API."""
        self.app = app
        self.alert_manager = alert_manager
        self.memory_monitor = memory_monitor
        self.alert_storage = None  # Will be set after initialization
        self.alert_aggregator = None  # Will be set after initialization

        # Initialize router
        self.router = APIRouter(prefix="/api")
        self._setup_routes()

    def _setup_routes(self):
        """Set up API routes."""
        # Alert endpoints
        self.router.add_api_route("/alerts/current", self.get_current_alerts, methods=["GET"])
        self.router.add_api_route("/alerts/history", self.get_alert_history, methods=["GET"])
        self.router.add_api_route("/alerts/summary", self.get_alert_summary, methods=["GET"])
        self.router.add_api_route("/alerts/{alert_id}/acknowledge", self.acknowledge_alert, methods=["POST"])
        self.router.add_api_route("/alerts/{alert_id}/resolve", self.resolve_alert, methods=["POST"])

        # Memory monitoring endpoints
        self.router.add_api_route("/memory/summary", self.get_memory_summary, methods=["GET"])
        self.router.add_api_route("/memory/pressure", self.get_memory_pressure, methods=["GET"])
        self.router.add_api_route("/memory/indices", self.get_index_memory, methods=["GET"])

        # Vector store endpoints
        self.router.add_api_route("/vectorstore/metrics", self.get_vectorstore_metrics, methods=["GET"])
        self.router.add_api_route("/vectorstore/performance", self.get_vectorstore_performance, methods=["GET"])

        # Service metrics endpoints
        self.router.add_api_route("/rate_limits", self.get_rate_limits, methods=["GET"])
        self.router.add_api_route("/errors", self.get_service_errors, methods=["GET"])

        # Alert aggregation endpoints
        self.router.add_api_route("/alerts/groups", self.get_alert_groups, methods=["GET"])
        self.router.add_api_route("/alerts/correlations", self.get_component_correlations, methods=["GET"])
        self.router.add_api_route("/alerts/trends", self.get_alert_trends, methods=["GET"])

    def _convert_mock_to_dict(self, mock_obj: Any) -> Dict:
        """Convert a mock object to a dictionary."""
        if hasattr(mock_obj, "__dict__"):
            return {k: v for k, v in mock_obj.__dict__.items() if not k.startswith("_")}
        return {}

    @cached_response(ttl=60)  # Cache for 1 minute
    async def get_memory_summary(self) -> Dict:
        """Get memory usage summary."""
        try:
            if any(x is None for x in [
                self.memory_monitor.total_memory,
                self.memory_monitor.used_memory,
                self.memory_monitor.available_memory,
                self.memory_monitor.memory_pressure
            ]):
                raise ValueError("Memory monitor returned invalid data")
            return {
                "total": self.memory_monitor.total_memory,
                "used": self.memory_monitor.used_memory,
                "available": self.memory_monitor.available_memory,
                "pressure": self.memory_monitor.memory_pressure
            }
        except Exception as e:
            logger.error(f"Failed to get memory summary: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get memory summary")

    @cached_response(ttl=30)  # Cache for 30 seconds
    async def get_memory_pressure(self) -> Dict:
        """Get memory pressure status."""
        try:
            if self.memory_monitor.memory_pressure is None:
                raise ValueError("Memory monitor returned invalid pressure data")
            return {"memory_pressure": self.memory_monitor.memory_pressure}
        except Exception as e:
            logger.error(f"Failed to get memory pressure: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get memory pressure")

    @cached_response(ttl=60)
    async def get_index_memory(self) -> Dict:
        """Get memory usage by index."""
        try:
            data = self.memory_monitor.get_index_memory()
            if data is None:
                raise ValueError("Memory monitor returned no index data")
            return data
        except Exception as e:
            logger.error(f"Failed to get index memory usage: {str(e)}")
            raise HTTPException(status_code=500, detail="Failed to get index memory usage")

    @cached_response(ttl=60)
    async def get_vectorstore_metrics(self) -> Dict:
        """Get vector store metrics."""
        metrics = {}
        for metric in REGISTRY.collect():
            if metric.name == VECTOR_STORE_SIZE._name:
                metrics["total_vectors"] = metric.samples[0].value
            elif metric.name == VECTOR_STORE_MEMORY._name:
                metrics["memory_usage"] = metric.samples[0].value
        return metrics

    @cached_response(ttl=60)
    async def get_vectorstore_performance(self) -> Dict:
        """Get vector store performance metrics."""
        metrics = {}
        for metric in REGISTRY.collect():
            if "store_type" in getattr(metric, "labels", {}):
                store_type = metric.labels["store_type"]
                if metric.name == "vector_search_seconds_sum":
                    metrics[f"search_time_sum_{store_type}"] = metric.value
                elif metric.name == "vector_search_seconds_count":
                    metrics[f"search_count_{store_type}"] = metric.value
        return metrics

    @cached_response(ttl=30)
    async def get_rate_limits(self) -> Dict:
        """Get rate limit status."""
        metrics = {}
        for metric in REGISTRY.collect():
            if metric.name == RATE_LIMITS_REMAINING._name:
                for sample in metric.samples:
                    if "service" in sample.labels:
                        metrics[f"rate_limits_remaining_{sample.labels['service']}"] = sample.value
        return metrics

    @cached_response(ttl=30)
    async def get_service_errors(self) -> Dict:
        """Get service error metrics."""
        metrics = {}
        for metric in REGISTRY.collect():
            if metric.name == API_ERRORS._name:
                for sample in metric.samples:
                    if "service" in sample.labels and "error_type" in sample.labels:
                        metrics[f"api_errors_total_{sample.labels['service']}_{sample.labels['error_type']}"] = sample.value
        return metrics

    # Alert endpoints don't use caching since they need to be real-time
    async def get_current_alerts(self) -> List[Dict]:
        """Get current alerts."""
        alerts = self.alert_storage.get_current_alerts()
        return [
            {**asdict(alert), "severity": alert.severity.upper() if hasattr(alert.severity, "upper") else alert.severity}
            for alert in alerts
        ]

    async def get_alert_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100
    ) -> List[Dict]:
        """Get alert history."""
        alerts = self.alert_storage.get_alert_history(start_time, end_time, limit)
        return [
            {**asdict(alert), "severity": alert.severity.upper() if hasattr(alert.severity, "upper") else alert.severity}
            for alert in alerts
        ]

    async def get_alert_summary(self) -> Dict:
        """Get alert summary."""
        summary = self.alert_storage.get_alert_summary()
        if isinstance(summary, dict):
            return asdict(AlertSummary(
                total_alerts=summary["total_alerts"],
                active_alerts=summary["active_alerts"],
                acknowledged_alerts=summary["acknowledged_alerts"],
                resolved_alerts=summary["resolved_alerts"]
            ))
        return asdict(summary)

    async def acknowledge_alert(self, alert_id: str) -> Dict:
        """Acknowledge an alert."""
        self.alert_storage.update_alert_status(alert_id, AlertStatus.ACKNOWLEDGED)
        return {"success": True, "message": "Alert acknowledged successfully"}

    async def resolve_alert(self, alert_id: str) -> Dict:
        """Resolve an alert."""
        self.alert_storage.update_alert_status(alert_id, AlertStatus.RESOLVED)
        return {"success": True, "message": "Alert resolved successfully"}

    @cached_response(ttl=300)  # Cache for 5 minutes
    async def get_alert_groups(self) -> List[Dict]:
        """Get alert groups."""
        groups = self.alert_aggregator.get_alert_groups()
        return [asdict(group) for group in groups]

    @cached_response(ttl=300)
    async def get_component_correlations(self) -> Dict[str, List[str]]:
        """Get correlated components based on alert patterns."""
        correlations = self.alert_aggregator.get_component_correlations()
        # Convert sets to lists for JSON serialization
        return {k: list(v) for k, v in correlations.items()}

    @cached_response(ttl=300)
    async def get_alert_trends(self) -> List[Dict]:
        """Get alert trends."""
        trends = self.alert_aggregator.get_alert_trends()
        return [asdict(trend) for trend in trends]
