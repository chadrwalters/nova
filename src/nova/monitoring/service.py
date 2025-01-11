"""Nova monitoring service."""

import asyncio
import logging
import os
import psutil
from typing import List
from nova.config import MonitoringConfig
from nova.monitoring.alerts import AlertManager
from nova.monitoring.metrics import (
    QUERY_LATENCY,
    QUERY_REQUESTS,
    QUERY_ERRORS,
    API_REQUESTS,
    API_ERRORS,
    MEMORY_USAGE,
    VECTOR_STORE_SIZE,
    VECTOR_STORE_MEMORY,
    RATE_LIMITS_REMAINING,
    RATE_LIMIT_RESETS,
    start_metrics_server
)

class MonitoringService:
    """Service for monitoring Nova system metrics."""

    def __init__(self, config: MonitoringConfig):
        """Initialize monitoring service.

        Args:
            config: Monitoring configuration
        """
        self.config = config
        self.alert_manager = AlertManager(config.alerting)
        self.logger = logging.getLogger(__name__)
        self._running = False
        self.tasks: List[asyncio.Task] = []

        # Setup logging
        if config.log_path:
            log_dir = os.path.dirname(config.log_path)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir)

            handler = logging.FileHandler(config.log_path)
            handler.setFormatter(logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            ))
            self.logger.addHandler(handler)
            self.logger.setLevel(logging.INFO)

    async def start(self) -> None:
        """Start the monitoring service if enabled."""
        if not self.config.enabled:
            self.logger.info("Monitoring disabled")
            return

        if self._running:
            self.logger.info("Monitoring service already running")
            return

        self.logger.info("Starting monitoring service")
        try:
            # Start metrics server
            start_metrics_server(
                port=self.config.metrics.port,
                host=self.config.metrics.host
            )
            self._running = True

            # Start collection tasks
            memory_task = asyncio.create_task(
                self._collect_memory_metrics(),
                name="memory_metrics"
            )
            vector_store_task = asyncio.create_task(
                self._collect_vector_store_metrics(),
                name="vector_store_metrics"
            )
            self.tasks.extend([memory_task, vector_store_task])

            # Add task completion callbacks
            for task in self.tasks:
                task.add_done_callback(self._handle_task_completion)

        except Exception as e:
            self.logger.error(f"Error starting monitoring service: {e}")
            await self.stop()

    def _handle_task_completion(self, task: asyncio.Task) -> None:
        """Handle completion of monitoring tasks."""
        try:
            task.result()  # This will raise any exceptions that occurred
        except asyncio.CancelledError:
            self.logger.info(f"Task {task.get_name()} was cancelled")
        except Exception as e:
            self.logger.error(f"Task {task.get_name()} failed with error: {e}")
            if self._running:  # Only restart if service is still meant to be running
                self.logger.info(f"Restarting task {task.get_name()}")
                new_task = asyncio.create_task(
                    self._collect_memory_metrics() if task.get_name() == "memory_metrics"
                    else self._collect_vector_store_metrics(),
                    name=task.get_name()
                )
                new_task.add_done_callback(self._handle_task_completion)
                self.tasks.append(new_task)

    async def stop(self) -> None:
        """Stop the monitoring service."""
        if not self._running:
            self.logger.info("Monitoring service already stopped")
            return

        self.logger.info("Stopping monitoring service")
        self._running = False

        # Cancel all tasks
        for task in self.tasks:
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self.tasks:
            try:
                await asyncio.gather(*self.tasks, return_exceptions=True)
            except asyncio.CancelledError:
                pass
            self.tasks.clear()

    def track_query(self, latency: float, query_type: str = "rag", error: bool = False, error_type: str = "timeout") -> None:
        """Track query latency and errors.

        Args:
            latency: Query latency in seconds
            query_type: Type of query (default: "rag")
            error: Whether the query resulted in an error
            error_type: Type of error if any (default: "timeout")
        """
        QUERY_LATENCY.labels(query_type=query_type).observe(latency)
        QUERY_REQUESTS.labels(query_type=query_type).inc()

        # Always check latency
        self.alert_manager.check_query_latency(latency)

        if error:
            QUERY_ERRORS.labels(error_type=error_type).inc()

    def track_api_request(self, service: str, error: bool = False, error_type: str = "api_error") -> None:
        """Track API requests and errors.

        Args:
            service: The API service being tracked (e.g., "openai", "anthropic")
            error: Whether the request resulted in an error
            error_type: Type of error if any
        """
        API_REQUESTS.labels(service=service).inc()
        if error:
            API_ERRORS.labels(service=service, error_type=error_type).inc()

        # Get current error count and total count for this service
        error_count = sum(
            API_ERRORS.labels(service=service, error_type=et)._value.get()
            for et in ["api_error", "test_error", "timeout"]
        )
        total_count = API_REQUESTS.labels(service=service)._value.get()

        # Always check error rate after updating metrics
        if total_count > 0:  # Only check if we have requests
            error_rate = error_count / total_count
            self.alert_manager.check_error_rate(error_count, total_count)

    def track_rate_limits(self, service: str, remaining: int, reset_time: int) -> None:
        """Track API rate limits.

        Args:
            service: The service being monitored (e.g., "openai", "anthropic")
            remaining: Number of API calls remaining
            reset_time: Time until rate limit reset in seconds
        """
        RATE_LIMITS_REMAINING.labels(service=service).set(remaining)
        RATE_LIMIT_RESETS.labels(service=service).set(reset_time)

        # Check if we're close to hitting limits
        self.alert_manager.check_rate_limits(service, remaining)

    async def _collect_memory_metrics(self) -> None:
        """Collect memory usage metrics periodically."""
        while self._running:
            try:
                process = psutil.Process(os.getpid())
                memory_bytes = process.memory_info().rss
                MEMORY_USAGE.set(memory_bytes)
                self.alert_manager.check_memory_usage(memory_bytes)
            except Exception as e:
                self.logger.error(f"Error collecting memory metrics: {e}")

            await asyncio.sleep(self.config.metrics.memory_update_interval)

    async def _collect_vector_store_metrics(self) -> None:
        """Collect vector store metrics periodically."""
        while self._running:
            try:
                size = self._get_vector_store_size()
                memory = self._get_vector_store_memory()
                VECTOR_STORE_SIZE.labels(store_type="faiss").set(size)
                VECTOR_STORE_MEMORY.labels(store_type="faiss").set(memory)
                self.alert_manager.check_vector_store_size(size)
            except Exception as e:
                self.logger.error(f"Error collecting vector store metrics: {e}")

            await asyncio.sleep(self.config.metrics.vector_store_update_interval)

    def _get_vector_store_size(self) -> int:
        """Get the current size of the vector store."""
        from nova.vector_store import get_vector_store
        try:
            store = get_vector_store()
            return store.index.ntotal if hasattr(store.index, 'ntotal') else 0
        except Exception as e:
            self.logger.error(f"Error getting vector store size: {e}")
            return 0

    def _get_vector_store_memory(self) -> int:
        """Get the current memory usage of the vector store."""
        from nova.vector_store import get_vector_store
        try:
            store = get_vector_store()
            # FAISS index memory = num_vectors * dimension * bytes_per_float
            num_vectors = store.index.ntotal if hasattr(store.index, 'ntotal') else 0
            dimension = store.index.d if hasattr(store.index, 'd') else 0
            bytes_per_float = 4  # float32
            return num_vectors * dimension * bytes_per_float
        except Exception as e:
            self.logger.error(f"Error getting vector store memory: {e}")
            return 0
