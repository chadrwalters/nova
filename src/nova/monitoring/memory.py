"""Memory management for Nova system.

This module handles memory tracking, cleanup, and OOM protection.
"""

import gc
import logging
import os
import psutil
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)


@dataclass
class MemoryLimits:
    """Memory limits configuration."""

    max_memory_mb: float = 1024.0  # 1GB default limit
    warning_threshold_mb: float = 768.0  # 75% of max
    cleanup_threshold_mb: float = 896.0  # 87.5% of max
    min_free_memory_mb: float = 128.0  # Minimum free memory required


class MemoryManager:
    """Manages memory usage and cleanup."""

    def __init__(self, base_path: Path, limits: Optional[MemoryLimits] = None):
        """Initialize memory manager.

        Args:
            base_path: Base path for Nova system
            limits: Optional memory limits configuration
        """
        self.base_path = base_path
        self.limits = limits or MemoryLimits()
        self.process = psutil.Process()
        self.peak_memory_mb = 0.0
        self.last_cleanup_time: Optional[datetime] = None
        self._memory_warnings = 0

    def check_memory(self) -> Dict[str, Any]:
        """Check current memory usage.

        Returns:
            Dict containing memory status and metrics
        """
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.peak_memory_mb = max(self.peak_memory_mb, current_memory)

        # Get system memory info
        system_memory = psutil.virtual_memory()
        available_mb = system_memory.available / 1024 / 1024

        # Check if we need to trigger cleanup
        needs_cleanup = (
            current_memory > self.limits.cleanup_threshold_mb
            or available_mb < self.limits.min_free_memory_mb
        )

        # Check if we're approaching limits
        is_warning = (
            current_memory > self.limits.warning_threshold_mb
            or available_mb < self.limits.min_free_memory_mb * 2
        )

        if needs_cleanup:
            self.cleanup_memory()
        elif is_warning:
            self._memory_warnings += 1
            logger.warning(
                f"Memory usage high: {current_memory:.1f}MB used, {available_mb:.1f}MB available"
            )

        return {
            "current_memory_mb": current_memory,
            "peak_memory_mb": self.peak_memory_mb,
            "available_memory_mb": available_mb,
            "warning_count": self._memory_warnings,
            "last_cleanup": self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
            "status": "critical" if needs_cleanup else "warning" if is_warning else "healthy",
        }

    def cleanup_memory(self) -> None:
        """Perform memory cleanup."""
        logger.info("Starting memory cleanup")
        start_memory = self.process.memory_info().rss / 1024 / 1024

        # Run garbage collection
        gc.collect()

        # Clear process memory
        if hasattr(os, "malloc_trim"):
            os.malloc_trim(0)  # type: ignore

        # Record cleanup time
        self.last_cleanup_time = datetime.now()

        # Log cleanup results
        end_memory = self.process.memory_info().rss / 1024 / 1024
        freed_mb = start_memory - end_memory
        logger.info(f"Memory cleanup complete: {freed_mb:.1f}MB freed")

    def check_oom_risk(self) -> bool:
        """Check if we're at risk of OOM.

        Returns:
            True if at risk of OOM, False otherwise
        """
        current_memory = self.process.memory_info().rss / 1024 / 1024
        system_memory = psutil.virtual_memory()
        available_mb = system_memory.available / 1024 / 1024

        return (
            current_memory > self.limits.max_memory_mb
            or available_mb < self.limits.min_free_memory_mb
        )

    def enforce_limits(self) -> None:
        """Enforce memory limits.

        Raises:
            MemoryError: If memory limits are exceeded and cannot be recovered
        """
        if self.check_oom_risk():
            # Try cleanup first
            self.cleanup_memory()

            # Check if cleanup helped
            if self.check_oom_risk():
                error_msg = (
                    f"Memory limits exceeded: {self.process.memory_info().rss / 1024 / 1024:.1f}MB used, "
                    f"limit is {self.limits.max_memory_mb}MB"
                )
                logger.error(error_msg)
                raise MemoryError(error_msg)

    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics.

        Returns:
            Dict containing memory statistics
        """
        current_memory = self.process.memory_info().rss / 1024 / 1024
        system_memory = psutil.virtual_memory()

        return {
            "process": {
                "current_memory_mb": current_memory,
                "peak_memory_mb": self.peak_memory_mb,
                "warning_count": self._memory_warnings,
                "last_cleanup": self.last_cleanup_time.isoformat() if self.last_cleanup_time else None,
            },
            "limits": {
                "max_memory_mb": self.limits.max_memory_mb,
                "warning_threshold_mb": self.limits.warning_threshold_mb,
                "cleanup_threshold_mb": self.limits.cleanup_threshold_mb,
                "min_free_memory_mb": self.limits.min_free_memory_mb,
            },
            "system": {
                "total_memory_mb": system_memory.total / 1024 / 1024,
                "available_memory_mb": system_memory.available / 1024 / 1024,
                "used_memory_mb": system_memory.used / 1024 / 1024,
                "memory_percent": system_memory.percent,
            },
        }
