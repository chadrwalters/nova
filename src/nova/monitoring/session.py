"""Session monitoring for Nova MCP server.

This module handles real-time monitoring during active Claude Desktop
sessions. It tracks performance metrics, health status, and errors while
the server is running.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class SessionMetrics:
    """Metrics collected during a session."""

    start_time: datetime
    queries_processed: int = 0
    total_query_time: float = 0.0
    peak_memory_mb: float = 0.0
    errors_encountered: int = 0
    last_error_time: datetime | None = None
    last_error_message: str | None = None


class SessionMonitor:
    """Monitors system health and performance during a Claude Desktop
    session."""

    def __init__(self, base_path: Path):
        """Initialize session monitor.

        Args:
            base_path: Base path for Nova system
        """
        self.base_path = base_path
        self.metrics = SessionMetrics(start_time=datetime.now())
        self.process = psutil.Process()

    def check_health(self) -> dict[str, Any]:
        """Perform quick health check of system components.

        Returns:
            Dict containing health status of components
        """
        vector_store_path = self.base_path / "vectors"
        processing_path = self.base_path / "processing"
        logs_path = self.base_path / "logs"

        return {
            "status": "active",
            "uptime_seconds": (datetime.now() - self.metrics.start_time).total_seconds(),
            "components": {
                "vector_store": {
                    "status": "healthy" if vector_store_path.exists() else "missing",
                    "path": str(vector_store_path),
                    "permissions": oct(vector_store_path.stat().st_mode)[-3:]
                    if vector_store_path.exists()
                    else None,
                },
                "processing": {
                    "status": "healthy" if processing_path.exists() else "missing",
                    "path": str(processing_path),
                },
                "logs": {
                    "status": "healthy" if logs_path.exists() else "missing",
                    "path": str(logs_path),
                },
            },
            "resources": {
                "memory_mb": self.process.memory_info().rss / 1024 / 1024,
                "cpu_percent": self.process.cpu_percent(),
                "disk_usage_percent": psutil.disk_usage(str(self.base_path)).percent,
            },
        }

    def record_query(self, query_time: float) -> None:
        """Record metrics for a processed query.

        Args:
            query_time: Time taken to process query in seconds
        """
        self.metrics.queries_processed += 1
        self.metrics.total_query_time += query_time

        # Update peak memory
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, current_memory)

    def record_error(self, error_message: str) -> None:
        """Record an error occurrence.

        Args:
            error_message: Error message to record
        """
        self.metrics.errors_encountered += 1
        self.metrics.last_error_time = datetime.now()
        self.metrics.last_error_message = error_message

    def get_session_stats(self) -> dict[str, Any]:
        """Get statistics for the current session.

        Returns:
            Dict containing session statistics
        """
        uptime = (datetime.now() - self.metrics.start_time).total_seconds()

        return {
            "session": {
                "start_time": self.metrics.start_time.isoformat(),
                "uptime_seconds": uptime,
                "queries_processed": self.metrics.queries_processed,
                "avg_query_time": (self.metrics.total_query_time / self.metrics.queries_processed)
                if self.metrics.queries_processed > 0
                else 0.0,
                "peak_memory_mb": self.metrics.peak_memory_mb,
                "current_memory_mb": self.process.memory_info().rss / 1024 / 1024,
                "errors": {
                    "count": self.metrics.errors_encountered,
                    "last_error_time": self.metrics.last_error_time.isoformat()
                    if self.metrics.last_error_time
                    else None,
                    "last_error_message": self.metrics.last_error_message,
                },
            },
            "resources": {
                "cpu_percent": self.process.cpu_percent(),
                "memory_percent": self.process.memory_percent(),
                "disk_usage_percent": psutil.disk_usage(str(self.base_path)).percent,
            },
        }

    def get_performance_metrics(self) -> dict[str, float]:
        """Get current performance metrics.

        Returns:
            Dict containing performance metrics
        """
        return {
            "cpu_percent": self.process.cpu_percent(),
            "memory_mb": self.process.memory_info().rss / 1024 / 1024,
            "memory_percent": self.process.memory_percent(),
            "avg_query_time": (self.metrics.total_query_time / self.metrics.queries_processed)
            if self.metrics.queries_processed > 0
            else 0.0,
        }
