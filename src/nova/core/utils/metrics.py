"""Metrics tracking utilities."""

from typing import Any, Dict, Optional
import asyncio
import time
from contextlib import asynccontextmanager


class MetricsTracker:
    """Track metrics during processing."""
    
    def __init__(self):
        """Initialize the metrics tracker."""
        self.metrics = {}
        self.timers = {}
        
    def increment(self, metric: str, value: int = 1) -> None:
        """Increment a metric counter.
        
        Args:
            metric: Name of the metric to increment
            value: Value to increment by (default: 1)
        """
        if metric not in self.metrics:
            self.metrics[metric] = 0
        self.metrics[metric] += value
        
    def add_timing(self, metric: str, duration: float) -> None:
        """Add a timing measurement.
        
        Args:
            metric: Name of the timing metric
            duration: Duration in seconds
        """
        if metric not in self.metrics:
            self.metrics[metric] = []
        self.metrics[metric].append(duration)
        
    def start_timer(self, name: str) -> None:
        """Start a timer.
        
        Args:
            name: Name of the timer
        """
        self.timers[name] = time.time()
        
    def stop_timer(self, name: str) -> float:
        """Stop a timer and return the duration.
        
        Args:
            name: Name of the timer
            
        Returns:
            Duration in seconds
            
        Raises:
            KeyError if timer was not started
        """
        if name not in self.timers:
            raise KeyError(f"Timer {name} was not started")
            
        duration = time.time() - self.timers[name]
        del self.timers[name]
        return duration
        
    @asynccontextmanager
    async def async_timer(self, name: str):
        """Async context manager for timing operations.
        
        Args:
            name: Name of the timer
            
        Yields:
            None
        """
        try:
            self.start_timer(name)
            yield
        finally:
            duration = self.stop_timer(name)
            self.add_timing(name, duration)
            
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics.
        
        Returns:
            Dictionary of metrics
        """
        return self.metrics
        
    def has_data(self) -> bool:
        """Check if any metrics have been recorded.
        
        Returns:
            True if metrics exist, False otherwise
        """
        return bool(self.metrics) 