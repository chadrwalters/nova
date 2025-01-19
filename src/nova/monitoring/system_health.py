"""System health monitoring module.

This module provides real-time system health monitoring capabilities
including memory, CPU, disk usage, and directory health checks.
"""

import logging
import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class MemoryMetrics:
    """Memory usage metrics."""

    current_mb: float
    peak_mb: float
    warning_threshold_mb: float = 1024.0  # 1GB default warning threshold
    critical_threshold_mb: float = 1536.0  # 1.5GB default critical threshold

    @property
    def status(self) -> str:
        """Get memory status based on thresholds."""
        if self.current_mb >= self.critical_threshold_mb:
            return "critical"
        elif self.current_mb >= self.warning_threshold_mb:
            return "warning"
        return "healthy"


@dataclass
class DiskMetrics:
    """Disk usage metrics."""

    total_gb: float
    used_gb: float
    free_gb: float
    warning_threshold_pct: float = 80.0
    critical_threshold_pct: float = 90.0

    @property
    def used_percent(self) -> float:
        """Get disk usage percentage."""
        return (self.used_gb / self.total_gb) * 100 if self.total_gb > 0 else 0

    @property
    def status(self) -> str:
        """Get disk status based on thresholds."""
        if self.used_percent >= self.critical_threshold_pct:
            return "critical"
        elif self.used_percent >= self.warning_threshold_pct:
            return "warning"
        return "healthy"


class SystemHealthMonitor:
    """Monitors system health metrics."""

    def __init__(
        self,
        base_path: Path,
        required_dirs: list[str] | None = None,
    ):
        """Initialize system health monitor.

        Args:
            base_path: Base path for Nova system
            required_dirs: List of required directory names relative to base_path
        """
        self.base_path = base_path
        self.required_dirs = required_dirs or ["vectors", "logs", "processing"]
        self.process = psutil.Process()
        self._peak_memory_mb = 0.0

    def get_memory_metrics(self) -> MemoryMetrics:
        """Get current memory usage metrics.

        Returns:
            MemoryMetrics object with current usage information
        """
        current_memory = self.process.memory_info().rss / (1024 * 1024)  # Convert to MB
        self._peak_memory_mb = max(self._peak_memory_mb, current_memory)

        return MemoryMetrics(
            current_mb=current_memory,
            peak_mb=self._peak_memory_mb,
        )

    def get_cpu_percent(self) -> float:
        """Get current CPU usage percentage.

        Returns:
            CPU usage percentage (0-100)
        """
        return self.process.cpu_percent()

    def get_disk_metrics(self) -> DiskMetrics:
        """Get disk usage metrics for Nova directory.

        Returns:
            DiskMetrics object with current usage information
        """
        disk_usage = psutil.disk_usage(str(self.base_path))
        return DiskMetrics(
            total_gb=disk_usage.total / (1024**3),  # Convert to GB
            used_gb=disk_usage.used / (1024**3),
            free_gb=disk_usage.free / (1024**3),
        )

    def check_directory_health(self) -> dict[str, str]:
        """Check health of required directories.

        Returns:
            Dictionary mapping directory names to their status
        """
        results = {}
        for dir_name in self.required_dirs:
            dir_path = self.base_path / dir_name
            if not dir_path.exists():
                results[dir_name] = "missing"
            elif not os.access(dir_path, os.R_OK | os.W_OK):
                results[dir_name] = "permission_error"
            else:
                results[dir_name] = "healthy"
        return results

    def get_system_health(self) -> dict[str, Any]:
        """Get comprehensive system health status.

        Returns:
            Dictionary containing all health metrics
        """
        memory_metrics = self.get_memory_metrics()
        disk_metrics = self.get_disk_metrics()
        dir_health = self.check_directory_health()
        cpu_percent = self.get_cpu_percent()

        # Determine overall status
        status = "healthy"
        if (
            memory_metrics.status == "critical"
            or disk_metrics.status == "critical"
            or "missing" in dir_health.values()
        ):
            status = "critical"
        elif (
            memory_metrics.status == "warning"
            or disk_metrics.status == "warning"
            or "permission_error" in dir_health.values()
        ):
            status = "warning"

        return {
            "timestamp": datetime.now().isoformat(),
            "status": status,
            "memory": {
                "current_mb": memory_metrics.current_mb,
                "peak_mb": memory_metrics.peak_mb,
                "status": memory_metrics.status,
            },
            "disk": {
                "total_gb": disk_metrics.total_gb,
                "used_gb": disk_metrics.used_gb,
                "free_gb": disk_metrics.free_gb,
                "used_percent": disk_metrics.used_percent,
                "status": disk_metrics.status,
            },
            "cpu_percent": cpu_percent,
            "directories": dir_health,
        }
