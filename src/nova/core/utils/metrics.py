"""Metrics tracking utilities."""

from typing import Dict, Any, Set, Optional, List
from datetime import datetime
import time
from contextlib import contextmanager, asynccontextmanager


class Timer:
    """Timer for tracking operation duration."""
    
    def __init__(self, name: str = None):
        """Initialize timer.
        
        Args:
            name: Optional name for the timer
        """
        self.name = name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
        
    def start(self) -> None:
        """Start the timer."""
        self.start_time = time.time()
        
    def stop(self) -> float:
        """Stop the timer and return duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time if self.start_time else 0
        return self.duration
        
    @property
    def is_stopped(self) -> bool:
        """Check if timer is stopped."""
        return self.end_time is not None


class MetricsTracker:
    """Track metrics for pipeline phases."""
    
    def __init__(self):
        """Initialize metrics tracker."""
        self.timers: Dict[str, Timer] = {}
        self.timer_history: Dict[str, List[float]] = {}
        self.counters: Dict[str, int] = {}
        self.gauges: Dict[str, float] = {}
        self.labels: Dict[str, Dict[str, Any]] = {}
        
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
            if name not in self.timer_history:
                self.timer_history[name] = []
            self.timer_history[name].append(duration)
            return duration
        return None
        
    def get_timer(self, name: str) -> Optional[float]:
        """Get timer duration.
        
        Args:
            name: Timer name
            
        Returns:
            Timer duration if exists and stopped
        """
        if name in self.timers and self.timers[name].is_stopped:
            return self.timers[name].duration
        return None
        
    def get_timer_history(self, name: str) -> List[float]:
        """Get timer history.
        
        Args:
            name: Timer name
            
        Returns:
            List of timer durations
        """
        return self.timer_history.get(name, [])
        
    def increment(self, name: str, value: int = 1) -> None:
        """Increment a named counter.
        
        Args:
            name: Counter name
            value: Value to increment by
        """
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value
        
    def get_counter(self, name: str) -> int:
        """Get counter value.
        
        Args:
            name: Counter name
            
        Returns:
            Counter value
        """
        return self.counters.get(name, 0)
        
    def set_gauge(self, name: str, value: float, labels: Optional[Dict[str, Any]] = None) -> None:
        """Set a gauge value.
        
        Args:
            name: Gauge name
            value: Gauge value
            labels: Optional labels
        """
        self.gauges[name] = value
        if labels:
            self.labels[name] = labels
            
    def get_gauge(self, name: str, labels: Optional[Dict[str, Any]] = None) -> float:
        """Get gauge value.
        
        Args:
            name: Gauge name
            labels: Optional labels
            
        Returns:
            Gauge value
        """
        if labels and name in self.labels:
            if self.labels[name] == labels:
                return self.gauges.get(name, 0)
            return 0
        return self.gauges.get(name, 0)
        
    def add_label(self, name: str, labels: Dict[str, Any]) -> None:
        """Add labels to a metric.
        
        Args:
            name: Metric name
            labels: Label dictionary
        """
        self.labels[name] = labels
        
    def has_data(self) -> bool:
        """Check if any metrics have been recorded.
        
        Returns:
            True if any metrics exist
        """
        return bool(self.timers or self.counters or self.gauges)
        
    def get_all_metrics(self) -> Dict[str, Any]:
        """Get all metrics.
        
        Returns:
            Dictionary of all metrics
        """
        return {
            "timers": {
                name: timer.duration
                for name, timer in self.timers.items()
                if timer.is_stopped
            },
            "timer_history": self.timer_history,
            "counters": self.counters,
            "gauges": self.gauges,
            "labels": self.labels
        }
        
    def reset(self) -> None:
        """Reset all metrics."""
        self.timers.clear()
        self.timer_history.clear()
        self.counters.clear()
        self.gauges.clear()
        self.labels.clear()
        
    @contextmanager
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
            
    @asynccontextmanager
    async def async_timer(self, name: str):
        """Async context manager for timing operations.
        
        Args:
            name: Timer name
        """
        self.start_timer(name)
        try:
            yield
        finally:
            self.stop_timer(name) 