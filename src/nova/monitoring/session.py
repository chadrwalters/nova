"""Session monitoring for Nova system."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from nova.monitoring.memory import MemoryManager, MemoryLimits
from nova.monitoring.persistent import PersistentMonitor
from nova.monitoring.profiler import Profiler
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class SessionMonitor:
    """Monitors Nova system session."""

    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        log_manager: Optional[PersistentMonitor] = None,
        monitor: Optional[PersistentMonitor] = None,
        nova_dir: Optional[Path] = None,
    ):
        """Initialize session monitor.

        Args:
            vector_store: Optional vector store instance
            log_manager: Optional log manager instance
            monitor: Optional persistent monitor instance
            nova_dir: Optional Nova system directory
        """
        logger.info("Initializing SessionMonitor with:")
        logger.info(f"  vector_store: {vector_store}")
        logger.info(f"  log_manager: {log_manager}")
        logger.info(f"  monitor: {monitor}")
        logger.info(f"  nova_dir: {nova_dir}")

        self.vector_store = vector_store
        self.log_manager = log_manager
        self.monitor = monitor
        self.nova_dir = nova_dir or Path(".nova")
        logger.info(f"Using nova_dir: {self.nova_dir}")

        logger.info("Creating MemoryManager")
        self.memory = MemoryManager(base_path=self.nova_dir)
        logger.info("Creating Profiler")
        self.profiler = Profiler(base_path=self.nova_dir)
        self.session_start = datetime.now()
        self.total_chunks = 0
        self.chunks_processed = 0
        self.processing_time = 0.0
        self.rebuild_errors: List[str] = []
        logger.info("SessionMonitor initialization complete")

    def check_health(self) -> Dict[str, Any]:
        """Check system health.

        Returns:
            Dict containing health status and metrics
        """
        # Check memory first
        memory_status = self.memory.check_memory()

        # Check vector store
        vector_store_status = "healthy"
        if self.vector_store:
            try:
                self.vector_store.check_health()
            except Exception as e:
                vector_store_status = f"error: {str(e)}"

        # Check persistent monitor
        monitor_status = "healthy"
        if self.monitor:
            try:
                self.monitor.check_health()
            except Exception as e:
                monitor_status = f"error: {str(e)}"

        # Check log manager
        log_status = "healthy"
        if self.log_manager:
            try:
                self.log_manager.check_health()
            except Exception as e:
                log_status = f"error: {str(e)}"

        return {
            "memory": memory_status,
            "vector_store": vector_store_status,
            "monitor": monitor_status,
            "logs": log_status,
            "session_uptime": (datetime.now() - self.session_start).total_seconds(),
            "status": (
                "critical"
                if memory_status["status"] == "critical"
                or any(
                    "error" in status
                    for status in [vector_store_status, monitor_status, log_status]
                )
                else "warning"
                if memory_status["status"] == "warning"
                else "healthy"
            ),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics.

        Returns:
            Dict containing system statistics
        """
        stats = {
            "memory": self.memory.get_memory_stats(),
            "session": {
                "start_time": self.session_start.isoformat(),
                "uptime": (datetime.now() - self.session_start).total_seconds(),
            },
            "profiles": self.profiler.get_profiles(),
        }

        if self.vector_store:
            stats["vector_store"] = self.vector_store.get_stats()

        if self.monitor:
            stats["monitor"] = self.monitor.get_stats()

        if self.log_manager:
            stats["logs"] = self.log_manager.get_stats()

        return stats

    def enforce_limits(self) -> None:
        """Enforce system limits."""
        self.memory.enforce_limits()

    def cleanup(self) -> None:
        """Perform system cleanup."""
        self.memory.cleanup_memory()
        self.profiler.cleanup_old_profiles()
        if self.vector_store:
            self.vector_store.cleanup()
        if self.monitor:
            self.monitor.cleanup()
        if self.log_manager:
            self.log_manager.cleanup()

    def configure_memory_limits(self, limits: MemoryLimits) -> None:
        """Configure memory limits.

        Args:
            limits: Memory limits configuration
        """
        self.memory.limits = limits

    def start_profile(self, name: str) -> Any:
        """Start profiling a code block.

        Args:
            name: Profile name

        Returns:
            Profile context manager
        """
        return self.profiler.profile(name)

    def get_profiles(self) -> List[Dict[str, Any]]:
        """Get list of available profiles.

        Returns:
            List of profile information
        """
        return self.profiler.get_profiles()

    def get_session_stats(self) -> Dict[str, Any]:
        """Get current session statistics.

        Returns:
            Dict containing session statistics
        """
        return {
            "session": {
                "start_time": self.session_start.isoformat(),
                "uptime": (datetime.now() - self.session_start).total_seconds(),
                "chunks_processed": self.chunks_processed,
                "total_chunks": self.total_chunks,
                "processing_time": self.processing_time,
                "errors": {
                    "count": len(self.rebuild_errors),
                    "last_error_time": self.rebuild_errors[-1] if self.rebuild_errors else None,
                    "last_error_message": self.rebuild_errors[-1] if self.rebuild_errors else None,
                }
            }
        }

    def track_rebuild_progress(self, total_chunks: int) -> None:
        """Track progress of vector store rebuild.

        Args:
            total_chunks: Total number of chunks to process
        """
        logger.info(f"Starting rebuild with {total_chunks} chunks")
        self.total_chunks = total_chunks
        self.chunks_processed = 0
        self.processing_time = 0.0
        self.rebuild_errors = []

    def update_rebuild_progress(self, chunks_processed: int, processing_time: float) -> None:
        """Update rebuild progress.

        Args:
            chunks_processed: Number of chunks processed
            processing_time: Total processing time in seconds
        """
        self.chunks_processed = chunks_processed
        self.processing_time = processing_time
        logger.info(f"Processed {chunks_processed}/{self.total_chunks} chunks in {processing_time:.1f}s")

    def record_rebuild_error(self, error_msg: str) -> None:
        """Record an error during rebuild.

        Args:
            error_msg: Error message
        """
        logger.error(f"Rebuild error: {error_msg}")
        self.rebuild_errors.append(error_msg)

    def complete_rebuild(self) -> None:
        """Mark rebuild as complete."""
        logger.info(f"Rebuild complete: {self.chunks_processed} chunks in {self.processing_time:.1f}s")
        if self.monitor:
            self.monitor.record_session_end(self.get_session_stats())
