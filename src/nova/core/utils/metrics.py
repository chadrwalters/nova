"""Metrics tracking utilities."""

# Standard library imports
import asyncio
import contextlib
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Generator, AsyncGenerator

# Third-party imports
import psutil

# Nova package imports
from nova.core.errors import ValidationError


@dataclass
class Timer:
    """Timer for tracking operation duration."""
    
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None
    
    def start(self) -> None:
        """Start the timer."""
        self.start_time = time.time()
        
    def stop(self) -> float:
        """Stop the timer and return duration.
        
        Returns:
            Duration in seconds
        """
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time if self.start_time else 0
        return self.duration


class TimingManager:
    """Manager for timing operations."""

    def __init__(self):
        """Initialize timing manager."""
        self.timers: Dict[str, Timer] = {}

    def start_timer(self, name: str) -> None:
        """Start a timer.
        
        Args:
            name: Timer name
        """
        if name not in self.timers:
            self.timers[name] = Timer(name)
        self.timers[name].start()

    def stop_timer(self, name: str) -> float:
        """Stop a timer and return elapsed time.
        
        Args:
            name: Timer name
            
        Returns:
            Elapsed time in seconds
        """
        if name not in self.timers:
            return 0.0
        return self.timers[name].stop()

    def get_elapsed_time(self, name: str) -> float:
        """Get elapsed time for a timer.
        
        Args:
            name: Timer name
            
        Returns:
            Elapsed time in seconds
        """
        if name not in self.timers:
            return 0.0
        return self.timers[name].elapsed_time

    @contextlib.contextmanager
    def timer(self, name: str):
        """Context manager for timing operations.
        
        Args:
            name: Timer name
        """
        self.start_timer(name)
        try:
            yield
        finally:
            self.stop_timer(name)


@dataclass
class MetricRecord:
    """Record of a single metric."""
    
    name: str
    value: Any
    timestamp: float = field(default_factory=time.time)
    tags: Optional[Dict[str, str]] = None
    metric_type: str = "metric"  # One of: metric, counter, gauge, timer
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metric record to dictionary.
        
        Returns:
            Dictionary representation of metric record
        """
        return {
            'name': self.name,
            'value': self.value,
            'timestamp': self.timestamp,
            'tags': self.tags or {},
            'type': self.metric_type
        }


@dataclass
class ResourceUsage:
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


@dataclass
class PhaseProgress:
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


class MetricsTracker:
    """Tracks metrics for monitoring and analysis."""
    
    def __init__(self):
        """Initialize metrics tracker."""
        self.metrics: List[MetricRecord] = []
        self.timers: Dict[str, Timer] = {}
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        
    def record_metric(self, name: str, value: Any, tags: Optional[Dict[str, str]] = None) -> None:
        """Record a metric.
        
        Args:
            name: Name of metric
            value: Value of metric
            tags: Optional tags to associate with metric
            
        Raises:
            ValidationError: If metric name is invalid
        """
        if not name:
            raise ValidationError("Metric name cannot be empty")
            
        metric = MetricRecord(
            name=name,
            value=value,
            tags=tags,
            metric_type="metric"
        )
        self.metrics.append(metric)
        
    def start_timer(self, name: str) -> None:
        """Start a named timer.
        
        Args:
            name: Timer name
        """
        if name not in self.timers:
            self.timers[name] = Timer()
        self.timers[name].start()
        
    def stop_timer(self, name: str) -> Optional[float]:
        """Stop a named timer and return duration.
        
        Args:
            name: Timer name
            
        Returns:
            Duration in seconds if timer exists
        """
        if name in self.timers:
            duration = self.timers[name].stop()
            self.record_metric(
                name=name,
                value=duration,
                tags={'type': 'duration'},
                metric_type="timer"
            )
            return duration
        return None
        
    def get_timer(self, name: str) -> Optional[Timer]:
        """Get a timer by name.
        
        Args:
            name: Timer name
            
        Returns:
            Timer if it exists
        """
        return self.timers.get(name)
        
    def increment_counter(self, name: str, amount: int = 1) -> None:
        """Increment a counter.
        
        Args:
            name: Counter name
            amount: Amount to increment by
        """
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += amount
        self.record_metric(
            name=name,
            value=self.counters[name],
            tags={'type': 'counter'},
            metric_type="counter"
        )
        
    def get_counter(self, name: str) -> int:
        """Get a counter value.
        
        Args:
            name: Counter name
            
        Returns:
            Counter value
        """
        return self.counters.get(name, 0)
        
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value.
        
        Args:
            name: Gauge name
            value: Gauge value
        """
        self.gauges[name] = value
        self.record_metric(
            name=name,
            value=value,
            tags={'type': 'gauge'},
            metric_type="gauge"
        )
        
    def get_gauge(self, name: str) -> float:
        """Get a gauge value.
        
        Args:
            name: Gauge name
            
        Returns:
            Gauge value
        """
        return self.gauges.get(name, 0.0)
        
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics.
        
        Returns:
            Dictionary containing all metrics, timers, counters, and gauges
        """
        return {
            'metrics': [m.to_dict() for m in self.metrics],
            'timers': {
                name: {
                    'start_time': timer.start_time,
                    'end_time': timer.end_time,
                    'duration': timer.duration
                }
                for name, timer in self.timers.items()
            },
            'counters': self.counters,
            'gauges': self.gauges
        }
        
    def clear(self) -> None:
        """Clear all metrics."""
        self.metrics.clear()
        self.timers.clear()
        self.counters.clear()
        self.gauges.clear()
        
    def __len__(self) -> int:
        """Get number of recorded metrics.
        
        Returns:
            Number of metrics
        """
        return len(self.metrics)


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

    def record_error(self, error: str) -> None:
        """Record an error.
        
        Args:
            error: Error message
        """
        self._metrics['errors'] += 1
        self.logger.error(error)

    async def async_capture_resource_usage(self) -> None:
        """Capture resource usage asynchronously."""
        try:
            self._metrics['resources'] = ResourceUsage.current()
        except Exception as e:
            self.logger.error(f"Error capturing resource usage: {str(e)}")

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