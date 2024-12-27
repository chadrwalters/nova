"""Monitoring utilities."""

import logging
import psutil
import contextlib
from typing import Dict, Any, Optional, Generator, AsyncGenerator
from pathlib import Path
from pydantic import BaseModel


class ResourceUsage(BaseModel):
    """Resource usage metrics."""
    
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_usage: float = 0.0

    @classmethod
    def current(cls) -> 'ResourceUsage':
        """Get current resource usage.
        
        Returns:
            Current resource usage
        """
        process = psutil.Process()
        disk = psutil.disk_usage('/')
        return cls(
            cpu_percent=process.cpu_percent(),
            memory_percent=process.memory_percent(),
            disk_usage=disk.percent
        )


class PhaseProgress(BaseModel):
    """Phase progress metrics."""
    
    total: int = 0
    processed: int = 0
    failed: int = 0
    skipped: int = 0

    @property
    def progress_percentage(self) -> float:
        """Get progress percentage.
        
        Returns:
            Progress percentage
        """
        if self.total == 0:
            return 0.0
        return (self.processed / self.total) * 100.0


class MonitoringManager:
    """Resource monitoring manager."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize monitoring manager.
        
        Args:
            config: Monitoring configuration
        """
        self.config = config or {}
        self.logger = logging.getLogger(__name__)
        self._metrics = {
            'resources': ResourceUsage(),
            'progress': PhaseProgress(),
            'counters': {},
            'gauges': {},
            'errors': 0
        }
        self._thresholds = {}
        self._process = psutil.Process()
        self._phases = {}

    def start(self) -> None:
        """Start monitoring."""
        self._sample_resource_usage()

    def stop(self) -> None:
        """Stop monitoring."""
        self._sample_resource_usage()

    def _sample_resource_usage(self) -> None:
        """Sample resource usage."""
        try:
            self._metrics['resources'] = ResourceUsage.current()
        except Exception as e:
            self.logger.error(f"Error sampling resource usage: {str(e)}")

    def update_progress(self, processed: int = 0, failed: int = 0, skipped: int = 0) -> None:
        """Update progress metrics.
        
        Args:
            processed: Number of processed items
            failed: Number of failed items
            skipped: Number of skipped items
        """
        progress = self._metrics['progress']
        progress.processed += processed
        progress.failed += failed
        progress.skipped += skipped
        progress.total = progress.processed + progress.failed + progress.skipped

    def get_metrics(self) -> Dict[str, Any]:
        """Get current metrics.
        
        Returns:
            Current metrics
        """
        self._sample_resource_usage()
        return {
            'resources': self._metrics['resources'].model_dump(),
            'progress': self._metrics['progress'].model_dump(),
            'counters': self._metrics['counters'],
            'gauges': self._metrics['gauges'],
            'errors': self._metrics['errors']
        }

    def get_progress(self) -> Dict[str, int]:
        """Get progress metrics.
        
        Returns:
            Progress metrics
        """
        return self._metrics['progress'].model_dump()

    def reset_progress(self) -> None:
        """Reset progress metrics."""
        self._metrics['progress'] = PhaseProgress()

    def get_resource_usage(self) -> Dict[str, float]:
        """Get resource usage metrics.
        
        Returns:
            Resource usage metrics
        """
        self._sample_resource_usage()
        return self._metrics['resources'].model_dump()

    def log_metrics(self) -> None:
        """Log current metrics."""
        metrics = self.get_metrics()
        resources = metrics['resources']
        progress = metrics['progress']
        
        self.logger.info(f"CPU Usage: {resources['cpu_percent']:.1f}%")
        self.logger.info(f"Memory Usage: {resources['memory_percent']:.1f}%")
        self.logger.info(f"Disk Usage: {resources['disk_usage']:.1f}%")
        self.logger.info(f"Progress: {progress}")

    def save_metrics(self, output_path: Path) -> None:
        """Save metrics to file.
        
        Args:
            output_path: Path to output file
        """
        try:
            metrics = self.get_metrics()
            output_path.write_text(str(metrics))
        except Exception as e:
            self.logger.error(f"Error saving metrics: {str(e)}")

    def cleanup(self) -> None:
        """Clean up monitoring resources."""
        self.stop()

    def set_threshold(self, metric: str, value: float) -> None:
        """Set threshold for metric.
        
        Args:
            metric: Metric name
            value: Threshold value
        """
        self._thresholds[metric] = value

    def register_phase(self, phase_name: str, total_items: Optional[int] = None) -> None:
        """Register pipeline phase.
        
        Args:
            phase_name: Phase name
            total_items: Total items to process
        """
        self._phases[phase_name] = {
            'progress': PhaseProgress(total=total_items or 0),
            'metrics': {
                'counters': {},
                'gauges': {},
                'errors': 0
            }
        }

    @contextlib.contextmanager
    def monitor_operation(self, operation_name: str) -> Generator[None, None, None]:
        """Monitor operation execution.
        
        Args:
            operation_name: Operation name
            
        Yields:
            None
        """
        start_usage = ResourceUsage.current()
        try:
            yield
        finally:
            end_usage = ResourceUsage.current()
            self.logger.debug(f"Operation {operation_name} resource usage:")
            self.logger.debug(f"  CPU: {end_usage.cpu_percent - start_usage.cpu_percent:.1f}%")
            self.logger.debug(f"  Memory: {end_usage.memory_percent - start_usage.memory_percent:.1f}%")

    @contextlib.asynccontextmanager
    async def async_monitor_operation(self, operation_name: str) -> AsyncGenerator[None, None]:
        """Monitor async operation execution.
        
        Args:
            operation_name: Operation name
            
        Yields:
            None
        """
        start_usage = ResourceUsage.current()
        try:
            yield
        finally:
            end_usage = ResourceUsage.current()
            self.logger.debug(f"Operation {operation_name} resource usage:")
            self.logger.debug(f"  CPU: {end_usage.cpu_percent - start_usage.cpu_percent:.1f}%")
            self.logger.debug(f"  Memory: {end_usage.memory_percent - start_usage.memory_percent:.1f}%")

    def increment_counter(self, name: str, value: int = 1, labels: Optional[Dict[str, str]] = None) -> None:
        """Increment counter metric.
        
        Args:
            name: Counter name
            value: Value to increment by
            labels: Metric labels
        """
        key = name
        if labels:
            key = f"{name}_{','.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        self._metrics['counters'][key] = self._metrics['counters'].get(key, 0) + value

    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, str]] = None) -> None:
        """Set gauge metric value.
        
        Args:
            name: Gauge name
            value: Gauge value
            labels: Metric labels
        """
        key = name
        if labels:
            key = f"{name}_{','.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        self._metrics['gauges'][key] = value

    def get_gauge(self, name: str, labels: Optional[Dict[str, str]] = None) -> float:
        """Get gauge metric value.
        
        Args:
            name: Gauge name
            labels: Metric labels
            
        Returns:
            Gauge value
        """
        key = name
        if labels:
            key = f"{name}_{','.join(f'{k}={v}' for k, v in sorted(labels.items()))}"
        return self._metrics['gauges'].get(key, 0.0)

    @property
    def metrics(self) -> Dict[str, Any]:
        """Get metrics dictionary.
        
        Returns:
            Metrics dictionary
        """
        return self._metrics 