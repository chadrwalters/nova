"""Rebuild monitoring functionality."""

import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import psutil

logger = logging.getLogger(__name__)


@dataclass
class RebuildMetrics:
    """Metrics collected during a rebuild operation."""

    start_time: datetime
    chunks_processed: int = 0
    total_chunks: int = 0
    processing_time: float = 0.0
    peak_memory_mb: float = 0.0
    errors_encountered: int = 0
    last_error_time: datetime | None = None
    last_error_message: str | None = None


class RebuildMonitor:
    """Monitors rebuild operations and tracks performance."""

    def __init__(self, base_path: Path):
        """Initialize rebuild monitor.

        Args:
            base_path: Base path for Nova system
        """
        self.base_path = base_path
        self.metrics = RebuildMetrics(start_time=datetime.now())
        self.process = psutil.Process()

    def check_rebuild_status(self) -> dict[str, Any]:
        """Check rebuild-specific health status.

        Returns:
            Dict containing rebuild health status
        """
        vector_store_path = self.base_path / "vectors"
        processing_path = self.base_path / "processing"
        cache_path = self.base_path / "cache"

        # Get disk usage only if base path exists
        try:
            disk_usage = psutil.disk_usage(str(self.base_path)).percent if self.base_path.exists() else 0.0
        except Exception:
            disk_usage = 0.0

        return {
            "status": "active" if self.metrics.chunks_processed > 0 else "idle",
            "progress": {
                "chunks_processed": self.metrics.chunks_processed,
                "total_chunks": self.metrics.total_chunks,
                "percent_complete": (
                    (self.metrics.chunks_processed / self.metrics.total_chunks * 100)
                    if self.metrics.total_chunks > 0
                    else 0.0
                ),
            },
            "components": {
                "vector_store": {
                    "status": "healthy" if vector_store_path.exists() else "missing",
                    "path": str(vector_store_path),
                },
                "processing": {
                    "status": "healthy" if processing_path.exists() else "missing",
                    "path": str(processing_path),
                },
                "cache": {
                    "status": "healthy" if cache_path.exists() else "missing",
                    "path": str(cache_path),
                },
            },
            "resources": {
                "memory_mb": self.process.memory_info().rss / 1024 / 1024,
                "cpu_percent": self.process.cpu_percent(),
                "disk_usage_percent": disk_usage,
            },
        }

    def update_progress(self, chunks_processed: int, total_chunks: int, time_taken: float) -> None:
        """Update rebuild progress metrics.

        Args:
            chunks_processed: Number of chunks processed
            total_chunks: Total number of chunks to process
            time_taken: Time taken for processing in seconds
        """
        self.metrics.chunks_processed = chunks_processed
        self.metrics.total_chunks = total_chunks
        self.metrics.processing_time = time_taken

        # Update peak memory
        current_memory = self.process.memory_info().rss / 1024 / 1024
        self.metrics.peak_memory_mb = max(self.metrics.peak_memory_mb, current_memory)

    def record_error(self, error_message: str) -> None:
        """Record a rebuild error.

        Args:
            error_message: Error message to record
        """
        self.metrics.errors_encountered += 1
        self.metrics.last_error_time = datetime.now()
        self.metrics.last_error_message = error_message

    def get_rebuild_stats(self) -> dict[str, Any]:
        """Get rebuild statistics.

        Returns:
            Dict containing rebuild statistics
        """
        elapsed_time = (datetime.now() - self.metrics.start_time).total_seconds()
        chunks_per_second = (
            self.metrics.chunks_processed / self.metrics.processing_time
            if self.metrics.processing_time > 0
            else 0.0
        )

        return {
            "rebuild": {
                "start_time": self.metrics.start_time.isoformat(),
                "elapsed_time": elapsed_time,
                "chunks_processed": self.metrics.chunks_processed,
                "total_chunks": self.metrics.total_chunks,
                "chunks_per_second": chunks_per_second,
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
