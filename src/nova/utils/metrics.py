"""Metrics tracking utilities."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional
import time

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
        """Stop the timer and return duration."""
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time if self.start_time else 0
        return self.duration

class MetricsTracker:
    """Tracks metrics for pipeline operations."""
    
    def __init__(self):
        """Initialize the metrics tracker."""
        self.timers: Dict[str, Timer] = {}
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
            return self.timers[name].stop()
        return None
    
    def get_timer(self, name: str) -> Optional[Timer]:
        """Get a timer by name.
        
        Args:
            name: Timer name
            
        Returns:
            Timer if it exists
        """
        return self.timers.get(name)
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a named counter.
        
        Args:
            name: Counter name
            value: Value to increment by
        """
        if name not in self.counters:
            self.counters[name] = 0
        self.counters[name] += value
    
    def set_gauge(self, name: str, value: float) -> None:
        """Set a gauge value.
        
        Args:
            name: Gauge name
            value: Gauge value
        """
        self.gauges[name] = value
    
    def add_label(self, name: str, labels: Dict[str, Any]) -> None:
        """Add labels to a metric.
        
        Args:
            name: Metric name
            labels: Label dictionary
        """
        self.labels[name] = labels
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get all metrics.
        
        Returns:
            Dictionary of all metrics
        """
        return {
            "timers": {
                name: {
                    "start_time": timer.start_time,
                    "end_time": timer.end_time,
                    "duration": timer.duration
                }
                for name, timer in self.timers.items()
            },
            "counters": self.counters,
            "gauges": self.gauges,
            "labels": self.labels
        }
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.timers.clear()
        self.counters.clear()
        self.gauges.clear()
        self.labels.clear() 