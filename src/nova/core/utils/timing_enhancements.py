"""Enhanced timing utilities."""

from typing import Dict, Any, Optional, List, Union
from contextlib import contextmanager
import time
import statistics
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
import json

from .timing import TimingManager
from .metrics import MetricsTracker
from ..errors import PipelineError

@dataclass
class TimingMetrics:
    """Detailed timing metrics for operations."""
    operation: str
    phase: Optional[str] = None
    start_time: float = field(default_factory=time.time)
    end_time: Optional[float] = None
    duration: Optional[float] = None
    labels: Dict[str, str] = field(default_factory=dict)
    metrics: Dict[str, Any] = field(default_factory=dict)

class TimingEnhancer:
    """Enhances timing functionality with additional features."""
    
    def __init__(
        self,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        metrics_dir: Optional[Union[str, Path]] = None,
        warn_threshold: float = 5.0,
        error_threshold: float = 10.0
    ):
        """Initialize timing enhancer.
        
        Args:
            timing: Optional timing manager instance
            metrics: Optional metrics tracker instance
            metrics_dir: Optional directory for storing metrics
            warn_threshold: Warning threshold in seconds
            error_threshold: Error threshold in seconds
        """
        self.timing = timing or TimingManager(warn_threshold, error_threshold)
        self.metrics = metrics or MetricsTracker()
        self.metrics_dir = Path(metrics_dir) if metrics_dir else None
        if self.metrics_dir:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize metrics storage
        self._phase_metrics: Dict[str, List[TimingMetrics]] = {}
        self._operation_metrics: Dict[str, List[TimingMetrics]] = {}
        self._benchmarks: Dict[str, List[float]] = {}
        
        # Performance thresholds
        self.warn_threshold = warn_threshold
        self.error_threshold = error_threshold
    
    @contextmanager
    def timed_operation(self, name: str, phase: Optional[str] = None, labels: Optional[Dict[str, str]] = None):
        """Context manager for timing operations with metrics tracking.
        
        Args:
            name: Operation name
            phase: Optional phase name
            labels: Optional labels to associate with the timing
            
        Yields:
            None
        """
        metrics = TimingMetrics(
            operation=name,
            phase=phase,
            labels=labels or {}
        )
        
        try:
            # Start timing
            metrics.start_time = time.time()
            yield
            
        finally:
            # Complete timing
            metrics.end_time = time.time()
            metrics.duration = metrics.end_time - metrics.start_time
            
            # Record metrics
            metrics.metrics.update({
                'timestamp': datetime.now().isoformat(),
                'duration': metrics.duration,
                'threshold_warnings': metrics.duration > self.warn_threshold,
                'threshold_errors': metrics.duration > self.error_threshold
            })
            
            # Store in appropriate collections
            if phase:
                if phase not in self._phase_metrics:
                    self._phase_metrics[phase] = []
                self._phase_metrics[phase].append(metrics)
            
            if name not in self._operation_metrics:
                self._operation_metrics[name] = []
            self._operation_metrics[name].append(metrics)
            
            # Record in timing manager
            with self.timing.timer(name):
                pass
            
            # Record in metrics tracker
            self.metrics.record_timing(name, metrics.duration)
            
            # Export metrics if directory configured
            if self.metrics_dir:
                self._export_metrics(metrics)
    
    def benchmark_operation(self, name: str, iterations: int = 1000) -> Dict[str, float]:
        """Benchmark an operation by running it multiple times.
        
        Args:
            name: Operation name
            iterations: Number of iterations
            
        Returns:
            Dictionary with benchmark statistics
        """
        if name not in self._benchmarks:
            self._benchmarks[name] = []
        
        durations = []
        for _ in range(iterations):
            start = time.time()
            with self.timing.timer(name):
                pass
            duration = time.time() - start
            durations.append(duration)
            self._benchmarks[name].append(duration)
        
        return {
            'min': min(durations),
            'max': max(durations),
            'mean': statistics.mean(durations),
            'median': statistics.median(durations),
            'stdev': statistics.stdev(durations) if len(durations) > 1 else 0
        }
    
    def get_phase_metrics(self, phase: str) -> Dict[str, Any]:
        """Get metrics for a specific phase.
        
        Args:
            phase: Phase name
            
        Returns:
            Dictionary with phase metrics
        """
        if phase not in self._phase_metrics:
            return {}
        
        metrics = self._phase_metrics[phase]
        durations = [m.duration for m in metrics if m.duration is not None]
        
        return {
            'count': len(metrics),
            'total_time': sum(durations),
            'average_time': statistics.mean(durations) if durations else 0,
            'min_time': min(durations) if durations else 0,
            'max_time': max(durations) if durations else 0,
            'operations': len(set(m.operation for m in metrics)),
            'warnings': sum(1 for m in metrics if m.duration and m.duration > self.warn_threshold),
            'errors': sum(1 for m in metrics if m.duration and m.duration > self.error_threshold)
        }
    
    def get_operation_metrics(self, operation: str) -> Dict[str, Any]:
        """Get metrics for a specific operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Dictionary with operation metrics
        """
        if operation not in self._operation_metrics:
            return {}
        
        metrics = self._operation_metrics[operation]
        durations = [m.duration for m in metrics if m.duration is not None]
        
        return {
            'count': len(metrics),
            'total_time': sum(durations),
            'average_time': statistics.mean(durations) if durations else 0,
            'min_time': min(durations) if durations else 0,
            'max_time': max(durations) if durations else 0,
            'phases': len(set(m.phase for m in metrics if m.phase)),
            'warnings': sum(1 for m in metrics if m.duration and m.duration > self.warn_threshold),
            'errors': sum(1 for m in metrics if m.duration and m.duration > self.error_threshold)
        }
    
    def get_timing_stats(self, name: str) -> Dict[str, float]:
        """Get timing statistics for an operation.
        
        Args:
            name: Operation name
            
        Returns:
            Dictionary with timing statistics
        """
        return self.metrics.get_timing_stats(name)
    
    def get_all_timings(self) -> Dict[str, Dict[str, Any]]:
        """Get all timing information.
        
        Returns:
            Dictionary with all timing information
        """
        return {
            'metrics': self.metrics.get_all_metrics(),
            'phases': {
                phase: self.get_phase_metrics(phase)
                for phase in self._phase_metrics
            },
            'operations': {
                op: self.get_operation_metrics(op)
                for op in self._operation_metrics
            },
            'benchmarks': {
                name: {
                    'iterations': len(durations),
                    'min': min(durations),
                    'max': max(durations),
                    'mean': statistics.mean(durations),
                    'median': statistics.median(durations),
                    'stdev': statistics.stdev(durations) if len(durations) > 1 else 0
                }
                for name, durations in self._benchmarks.items()
            }
        }
    
    def _export_metrics(self, metrics: TimingMetrics) -> None:
        """Export metrics to file.
        
        Args:
            metrics: Timing metrics to export
        """
        try:
            if not self.metrics_dir:
                return
                
            # Create metrics file path
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            metrics_file = self.metrics_dir / f"{metrics.operation}_{timestamp}.json"
            
            # Export metrics
            with open(metrics_file, 'w') as f:
                json.dump({
                    'operation': metrics.operation,
                    'phase': metrics.phase,
                    'start_time': metrics.start_time,
                    'end_time': metrics.end_time,
                    'duration': metrics.duration,
                    'labels': metrics.labels,
                    'metrics': metrics.metrics
                }, f, indent=2)
                
        except Exception as e:
            raise PipelineError(f"Failed to export metrics: {e}")
    
    def clear(self):
        """Clear all timing information."""
        self.timing.clear()
        self.metrics.clear()
        self._phase_metrics.clear()
        self._operation_metrics.clear()
        self._benchmarks.clear() 