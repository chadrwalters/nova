"""Resource management functionality."""

import asyncio
import os
import psutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, AsyncContextManager
from contextlib import asynccontextmanager

import structlog

from src.core.exceptions import ProcessingError

logger = structlog.get_logger(__name__)


@dataclass
class ResourceLimits:
    """Resource limits configuration."""
    max_memory_mb: int = int(os.getenv("NOVA_MAX_MEMORY_MB", "4096"))  # 4GB default
    max_disk_usage_mb: int = int(os.getenv("NOVA_MAX_DISK_MB", "20480"))  # 20GB default
    max_cpu_percent: float = float(os.getenv("NOVA_MAX_CPU_PERCENT", "80.0"))


class ResourceManager:
    """Manages system resources and file locking."""

    def __init__(self, limits: Optional[ResourceLimits] = None) -> None:
        """Initialize resource manager.

        Args:
            limits: Optional resource limits configuration
        """
        self.limits = limits or ResourceLimits()
        self.logger = logger
        self._locks = {}

    async def check_resources(self) -> None:
        """Check system resource usage against limits.

        Raises:
            ProcessingError: If resource limits are exceeded
        """
        try:
            # Check memory usage
            memory = psutil.Process().memory_info().rss / 1024 / 1024  # MB
            if memory > self.limits.max_memory_mb:
                raise ProcessingError(
                    f"Memory usage ({memory:.1f}MB) exceeds limit "
                    f"({self.limits.max_memory_mb}MB)"
                )

            # Check disk usage
            disk = psutil.disk_usage("/").used / 1024 / 1024  # MB
            if disk > self.limits.max_disk_usage_mb:
                raise ProcessingError(
                    f"Disk usage ({disk:.1f}MB) exceeds limit "
                    f"({self.limits.max_disk_usage_mb}MB)"
                )

            # Check CPU usage
            cpu = psutil.cpu_percent(interval=0.1)
            if cpu > self.limits.max_cpu_percent:
                raise ProcessingError(
                    f"CPU usage ({cpu:.1f}%) exceeds limit "
                    f"({self.limits.max_cpu_percent}%)"
                )

        except Exception as e:
            self.logger.error("Resource check failed", error=str(e))
            raise ProcessingError(f"Resource check failed: {e}")

    @asynccontextmanager
    async def file_lock(self, file_path: Path) -> AsyncContextManager[None]:
        """Get a lock for file operations.

        Args:
            file_path: Path to the file to lock

        Returns:
            AsyncContextManager for the file lock
        """
        if str(file_path) not in self._locks:
            self._locks[str(file_path)] = asyncio.Lock()
        
        lock = self._locks[str(file_path)]
        try:
            await lock.acquire()
            yield
        finally:
            lock.release()

    async def cleanup(self) -> None:
        """Clean up resources and release locks."""
        try:
            # Clear locks
            self._locks.clear()

            # Run garbage collection
            import gc
            gc.collect()

        except Exception as e:
            self.logger.error("Resource cleanup failed", error=str(e))
            if not getattr(self, "error_tolerance", False):
                raise ProcessingError(f"Resource cleanup failed: {e}") 