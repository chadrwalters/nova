"""Timing utilities for measuring operation durations."""

import time
import contextlib
from typing import Dict, Optional, Any, List

from ..errors import PipelineError

class TimingManager:
    """Manager for tracking operation timing."""
    
    def __init__(self, warn_threshold: float = 5.0, error_threshold: float = 10.0):
        """Initialize timing manager.
        
        Args:
            warn_threshold: Threshold in seconds for warning
            error_threshold: Threshold in seconds for error
        """
        self.warn_threshold = warn_threshold
        self.error_threshold = error_threshold
        self._timings: Dict[str, List[float]] = {}
        self._active_timers: Dict[str, float] = {}
        
    def has_data(self) -> bool:
        """Check if there are any timing records.
        
        Returns:
            bool: True if there are timing records, False otherwise
        """
        return bool(self._timings)
        
    def start_timer(self, operation: str, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Start timing an operation.
        
        Args:
            operation: Name of operation to time
            metadata: Optional metadata about the operation
        """
        self._active_timers[operation] = time.time()
        
    def stop_timer(self, operation: str) -> float:
        """Stop timing an operation.
        
        Args:
            operation: Name of operation to stop timing
            
        Returns:
            Duration in seconds
            
        Raises:
            PipelineError: If operation was not started
        """
        if operation not in self._active_timers:
            raise PipelineError(f"Timer not started for operation: {operation}")
            
        start_time = self._active_timers.pop(operation)
        duration = time.time() - start_time
        
        if operation not in self._timings:
            self._timings[operation] = []
        self._timings[operation].append(duration)
        
        return duration
        
    @contextlib.contextmanager
    def timer(self, operation: str) -> None:
        """Time an operation using context manager.
        
        Args:
            operation: Name of operation to time
        """
        try:
            start_time = time.time()
            yield
            duration = time.time() - start_time
            
            if operation not in self._timings:
                self._timings[operation] = []
            self._timings[operation].append(duration)
            
            if duration > self.error_threshold:
                raise PipelineError(f"Operation {operation} took {duration:.2f}s (error threshold: {self.error_threshold}s)")
            elif duration > self.warn_threshold:
                print(f"Warning: Operation {operation} took {duration:.2f}s (warning threshold: {self.warn_threshold}s)")
                
        except Exception as e:
            if not isinstance(e, PipelineError):
                raise PipelineError(f"Error timing operation {operation}: {e}")
            raise
            
    def get_timing(self, operation: str) -> Optional[float]:
        """Get average timing for operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Average duration in seconds or None if no timings
        """
        try:
            if operation not in self._timings:
                return None
                
            timings = self._timings[operation]
            if not timings:
                return None
                
            return sum(timings) / len(timings)
            
        except Exception as e:
            raise PipelineError(f"Failed to get timing for {operation}: {e}")
            
    def get_all_timings(self) -> Dict[str, float]:
        """Get all operation timings.
        
        Returns:
            Dict mapping operation names to average durations
        """
        try:
            return {
                op: self.get_timing(op)
                for op in self._timings.keys()
            }
            
        except Exception as e:
            raise PipelineError(f"Failed to get all timings: {e}")
            
    def clear_timings(self) -> None:
        """Clear all timing data."""
        try:
            self._timings.clear()
            
        except Exception as e:
            raise PipelineError(f"Failed to clear timings: {e}")
            
    def get_timing_stats(self, operation: str) -> Dict[str, Any]:
        """Get timing statistics for operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Dict with timing statistics
        """
        try:
            if operation not in self._timings:
                return {}
                
            timings = self._timings[operation]
            if not timings:
                return {}
                
            return {
                'count': len(timings),
                'total': sum(timings),
                'average': sum(timings) / len(timings),
                'min': min(timings),
                'max': max(timings)
            }
            
        except Exception as e:
            raise PipelineError(f"Failed to get timing stats for {operation}: {e}")
            
    def get_all_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get timing statistics for all operations.
        
        Returns:
            Dict mapping operation names to timing statistics
        """
        try:
            return {
                op: self.get_timing_stats(op)
                for op in self._timings.keys()
            }
            
        except Exception as e:
            raise PipelineError(f"Failed to get all timing stats: {e}")
            
    def check_thresholds(self, operation: str) -> None:
        """Check timing thresholds for operation.
        
        Args:
            operation: Operation name
        """
        try:
            if operation not in self._timings:
                return
                
            avg_time = self.get_timing(operation)
            if avg_time is None:
                return
                
            if avg_time > self.error_threshold:
                raise PipelineError(f"Operation {operation} average time {avg_time:.2f}s exceeds error threshold {self.error_threshold}s")
            elif avg_time > self.warn_threshold:
                print(f"Warning: Operation {operation} average time {avg_time:.2f}s exceeds warning threshold {self.warn_threshold}s")
                
        except Exception as e:
            if not isinstance(e, PipelineError):
                raise PipelineError(f"Failed to check thresholds for {operation}: {e}")
            raise
            
    def check_all_thresholds(self) -> None:
        """Check timing thresholds for all operations."""
        try:
            for operation in self._timings.keys():
                self.check_thresholds(operation)
                
        except Exception as e:
            raise PipelineError(f"Failed to check all thresholds: {e}")
            
    def get_slow_operations(self, threshold: Optional[float] = None) -> List[str]:
        """Get list of operations exceeding threshold.
        
        Args:
            threshold: Optional threshold in seconds (defaults to warning threshold)
            
        Returns:
            List of operation names
        """
        try:
            if threshold is None:
                threshold = self.warn_threshold
                
            return [
                op for op in self._timings.keys()
                if self.get_timing(op) is not None and self.get_timing(op) > threshold
            ]
            
        except Exception as e:
            raise PipelineError(f"Failed to get slow operations: {e}")
            
    def get_timing_summary(self) -> str:
        """Get timing summary string.
        
        Returns:
            Summary string
        """
        try:
            lines = []
            for op in sorted(self._timings.keys()):
                stats = self.get_timing_stats(op)
                if not stats:
                    continue
                    
                lines.append(f"{op}:")
                lines.append(f"  Count: {stats['count']}")
                lines.append(f"  Total: {stats['total']:.2f}s")
                lines.append(f"  Average: {stats['average']:.2f}s")
                lines.append(f"  Min: {stats['min']:.2f}s")
                lines.append(f"  Max: {stats['max']:.2f}s")
                
            return "\n".join(lines)
            
        except Exception as e:
            raise PipelineError(f"Failed to get timing summary: {e}")
            
    def __str__(self) -> str:
        """Get string representation.
        
        Returns:
            String representation
        """
        return self.get_timing_summary() 