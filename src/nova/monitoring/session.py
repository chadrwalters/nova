"""Session monitoring for Nova system."""

import logging
from datetime import datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict

from nova.monitoring.memory import MemoryLimits, MemoryManager
from nova.monitoring.metrics import SessionMetrics
from nova.monitoring.persistent import PersistentMonitor
from nova.monitoring.profiler import Profiler
from nova.vector_store.store import HealthData, VectorStore

logger = logging.getLogger(__name__)


class SessionHealthData(TypedDict):
    """Session health data."""

    memory: dict[str, Any]
    vector_store: str
    monitor: str
    logs: str
    session_uptime: float
    status: str
    repository: dict[str, Any]
    collection: dict[str, Any]
    database_status: str
    error: NotRequired[str]


class CollectionStats(TypedDict):
    """Collection statistics."""

    name: str
    count: int
    embeddings: int
    size: int


class SessionMonitor:
    """Monitors Nova system session."""

    def __init__(
        self,
        vector_store: VectorStore | None = None,
        log_manager: PersistentMonitor | None = None,
        monitor: PersistentMonitor | None = None,
        nova_dir: Path | None = None,
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
        self.metrics = SessionMetrics(start_time=self.session_start)
        logger.info("SessionMonitor initialization complete")

    def check_health(self) -> SessionHealthData:
        """Check system health.

        Returns:
            Dict containing health status and metrics
        """
        # Check memory first
        memory_status = self.memory.check_memory()

        # Check vector store and get detailed stats
        vector_store_status = "healthy"
        vector_store_health: HealthData | None = None
        if self.vector_store:
            try:
                vector_store_health = self.vector_store.check_health()
                # Check if we have documents but can't access them
                collection = vector_store_health.get("collection", {})
                if collection.get("exists", False):
                    if collection.get("count", 0) == 0:
                        vector_store_status = "degraded"
                        logger.warning("Vector store is empty but collection exists")
                else:
                    vector_store_status = "degraded"
                    logger.warning("Vector store collection does not exist")
            except Exception as e:
                vector_store_status = f"error: {e!s}"
                logger.error(f"Vector store health check failed: {e}", exc_info=True)

        # Check persistent monitor
        monitor_status = "healthy"
        if self.monitor:
            try:
                self.monitor.check_health()
            except Exception as e:
                monitor_status = f"error: {e!s}"
                logger.error(f"Monitor health check failed: {e}", exc_info=True)

        # Check log manager
        log_status = "healthy"
        if self.log_manager:
            try:
                self.log_manager.check_health()
            except Exception as e:
                log_status = f"error: {e!s}"
                logger.error(f"Log manager health check failed: {e}", exc_info=True)

        # Build complete health status
        health_status: SessionHealthData = {
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
                or "degraded" in [vector_store_status, monitor_status, log_status]
                else "healthy"
            ),
            "repository": {},
            "collection": {},
            "database_status": "disconnected",
        }

        # Include vector store details if available
        if vector_store_health:
            # Get repository and collection data
            repository_data = vector_store_health.get("repository", {})
            collection_data = vector_store_health.get("collection", {})

            # Convert to Dict[str, Any] using dict comprehension to ensure type safety
            repository = {str(k): v for k, v in repository_data.items()}
            collection = {str(k): v for k, v in collection_data.items()}

            health_status["repository"] = repository
            health_status["collection"] = collection
            health_status["database_status"] = (
                "connected" if collection.get("exists", False) else "disconnected"
            )

        return health_status

    def get_stats(self) -> dict[str, Any]:
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

    def get_profiles(self) -> list[dict[str, Any]]:
        """Get list of available profiles.

        Returns:
            List of profile information
        """
        return self.profiler.get_profiles()

    def track_rebuild_progress(self, total_chunks: int) -> None:
        """Track progress of vector store rebuild.

        Args:
            total_chunks: Total number of chunks to process
        """
        logger.info(f"Starting rebuild with {total_chunks} chunks")
        self.metrics.rebuild_start_time = datetime.now()
        self.metrics.total_chunks = total_chunks
        self.metrics.chunks_processed = 0
        self.metrics.processing_time = 0.0
        self.metrics.rebuild_errors = 0
        self.metrics.rebuild_last_error_time = None
        self.metrics.rebuild_last_error_message = None
        self.metrics.rebuild_peak_memory_mb = 0.0

    def update_rebuild_progress(self, chunks_processed: int, processing_time: float) -> None:
        """Update rebuild progress.

        Args:
            chunks_processed: Number of chunks processed
            processing_time: Total processing time in seconds
        """
        self.metrics.chunks_processed = chunks_processed
        self.metrics.processing_time = processing_time
        # Update peak memory
        current_memory = self.memory.get_memory_stats()["process"]["current_memory_mb"]
        self.metrics.rebuild_peak_memory_mb = max(
            self.metrics.rebuild_peak_memory_mb, current_memory
        )
        logger.info(
            f"Processed {chunks_processed}/{self.metrics.total_chunks} chunks in {processing_time:.1f}s"
        )

    def record_rebuild_error(self, error_msg: str) -> None:
        """Record an error during rebuild.

        Args:
            error_msg: Error message
        """
        logger.error(f"Rebuild error: {error_msg}")
        self.metrics.rebuild_errors += 1
        self.metrics.rebuild_last_error_time = datetime.now()
        self.metrics.rebuild_last_error_message = error_msg

    def complete_rebuild(self) -> None:
        """Mark rebuild as complete."""
        logger.info(
            f"Rebuild complete: {self.metrics.chunks_processed} chunks in {self.metrics.processing_time:.1f}s"
        )
        self.metrics.rebuild_end_time = datetime.now()
        if self.monitor:
            self.monitor.record_session_end(self.get_session_stats())

    def get_session_stats(self) -> dict[str, Any]:
        """Get current session statistics.

        Returns:
            Dict containing session statistics
        """
        return {
            "session": {
                "start_time": self.session_start.isoformat(),
                "uptime": (datetime.now() - self.session_start).total_seconds(),
                "chunks_processed": self.metrics.chunks_processed,
                "total_chunks": self.metrics.total_chunks,
                "processing_time": self.metrics.processing_time,
                "errors": {
                    "count": self.metrics.rebuild_errors,
                    "last_error_time": self.metrics.rebuild_last_error_time.isoformat()
                    if self.metrics.rebuild_last_error_time
                    else None,
                    "last_error_message": self.metrics.rebuild_last_error_message,
                },
            }
        }

    def get_rebuild_stats(self) -> dict[str, Any]:
        """Get rebuild statistics.

        Returns:
            Dict containing rebuild statistics
        """
        if not self.metrics.rebuild_start_time:
            return {"status": "not_started"}

        elapsed_time = (datetime.now() - self.metrics.rebuild_start_time).total_seconds()
        chunks_per_second = self.metrics.chunks_processed / elapsed_time if elapsed_time > 0 else 0

        stats = {
            "status": "completed" if self.metrics.rebuild_end_time else "in_progress",
            "progress": {
                "chunks_processed": self.metrics.chunks_processed,
                "total_chunks": self.metrics.total_chunks,
                "percent_complete": (
                    self.metrics.chunks_processed / self.metrics.total_chunks * 100
                    if self.metrics.total_chunks > 0
                    else 0
                ),
            },
            "timing": {
                "start_time": self.metrics.rebuild_start_time.isoformat(),
                "end_time": self.metrics.rebuild_end_time.isoformat()
                if self.metrics.rebuild_end_time
                else None,
                "processing_time": self.metrics.processing_time,
            },
            "performance": {
                "chunks_per_second": chunks_per_second,
                "peak_memory_mb": self.metrics.rebuild_peak_memory_mb,
            },
            "errors": {
                "count": self.metrics.rebuild_errors,
                "last_error_time": self.metrics.rebuild_last_error_time.isoformat()
                if self.metrics.rebuild_last_error_time
                else None,
                "last_error_message": self.metrics.rebuild_last_error_message,
            },
        }

        return stats

    def get_collection_stats(self) -> dict[str, CollectionStats]:
        """Get collection statistics.

        Returns:
            Dict[str, CollectionStats]: Collection statistics
        """
        stats: dict[str, CollectionStats] = {}
        if self.vector_store:
            for collection in self.vector_store.list_collections():
                stats[collection.name] = CollectionStats(
                    name=collection.name,
                    count=collection.count(),
                    embeddings=collection.embeddings(),
                    size=collection.size(),
                )
        return stats
