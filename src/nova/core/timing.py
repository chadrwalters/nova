"""Timing utilities."""

import time
from contextlib import contextmanager
from typing import Dict, Optional


class Timer:
    """Timer for measuring execution time."""

    def __init__(self, name: str):
        """Initialize timer.
        
        Args:
            name: Timer name
        """
        self.name = name
        self.start_time = None
        self.end_time = None

    def start(self) -> None:
        """Start timer."""
        self.start_time = time.time()

    def stop(self) -> float:
        """Stop timer and return elapsed time.
        
        Returns:
            Elapsed time in seconds
        """
        self.end_time = time.time()
        return self.elapsed_time

    @property
    def elapsed_time(self) -> float:
        """Get elapsed time.
        
        Returns:
            Elapsed time in seconds
        """
        if self.start_time is None:
            return 0.0
        end = self.end_time or time.time()
        return end - self.start_time


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