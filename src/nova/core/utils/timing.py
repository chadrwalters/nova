"""Timing utilities."""

import time
from typing import Dict, Any, Optional
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class Timer:
    """Timer for measuring execution time."""
    name: str
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    duration: Optional[float] = None

    def start(self) -> None:
        """Start the timer."""
        self.start_time = time.time()
        
    def stop(self) -> float:
        """Stop the timer.
        
        Returns:
            Duration in seconds
        """
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
        return self.duration
        
    def reset(self) -> None:
        """Reset the timer."""
        self.start_time = None
        self.end_time = None
        self.duration = None


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
        """Stop a timer.
        
        Args:
            name: Timer name
            
        Returns:
            Duration in seconds
        """
        if name not in self.timers:
            raise KeyError(f"Timer {name} not found")
        return self.timers[name].stop()
        
    def get_timer(self, name: str) -> Timer:
        """Get a timer.
        
        Args:
            name: Timer name
            
        Returns:
            Timer instance
        """
        if name not in self.timers:
            raise KeyError(f"Timer {name} not found")
        return self.timers[name]
        
    def reset_timer(self, name: str) -> None:
        """Reset a timer.
        
        Args:
            name: Timer name
        """
        if name not in self.timers:
            raise KeyError(f"Timer {name} not found")
        self.timers[name].reset()
        
    def clear(self) -> None:
        """Clear all timers."""
        self.timers.clear()
        
    @contextmanager
    def timer(self, name: str) -> Timer:
        """Context manager for timing operations.
        
        Args:
            name: Timer name
            
        Returns:
            Timer instance
        """
        try:
            self.start_timer(name)
            yield self.timers[name]
        finally:
            self.stop_timer(name)
            
    def get_all_timers(self) -> Dict[str, Timer]:
        """Get all timers.
        
        Returns:
            Dict of timer name to timer instance
        """
        return self.timers 