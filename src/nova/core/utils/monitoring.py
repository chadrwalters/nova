"""Monitoring utilities."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json
import time

from ..errors import PipelineError

class MonitoringManager:
    """Manager for monitoring pipeline operations."""
    
    def __init__(self, metrics_dir: Optional[Union[str, Path]] = None):
        """Initialize monitoring manager.
        
        Args:
            metrics_dir: Optional directory for storing monitoring data
        """
        self.metrics_dir = Path(metrics_dir) if metrics_dir else None
        if self.metrics_dir:
            self.metrics_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize state
        self.state = {
            "status": "initialized",
            "start_time": None,
            "end_time": None,
            "duration": None,
            "error": None
        }
        
        # Initialize metrics
        self.metrics = {
            "files_processed": 0,
            "files_failed": 0,
            "warnings": 0,
            "errors": 0,
            "timings": {}
        }
    
    def start(self) -> None:
        """Start monitoring."""
        try:
            self.state["status"] = "running"
            self.state["start_time"] = time.time()
            
        except Exception as e:
            raise PipelineError(f"Failed to start monitoring: {e}")
    
    def stop(self) -> None:
        """Stop monitoring."""
        try:
            self.state["status"] = "completed"
            self.state["end_time"] = time.time()
            self.state["duration"] = self.state["end_time"] - self.state["start_time"]
            
        except Exception as e:
            raise PipelineError(f"Failed to stop monitoring: {e}")
    
    def record_timing(self, operation: str, duration: float) -> None:
        """Record timing for an operation.
        
        Args:
            operation: Operation name
            duration: Duration in seconds
        """
        try:
            if operation not in self.metrics["timings"]:
                self.metrics["timings"][operation] = []
            self.metrics["timings"][operation].append(duration)
            
        except Exception as e:
            raise PipelineError(f"Failed to record timing: {e}")
    
    def increment_counter(self, name: str, value: int = 1) -> None:
        """Increment a counter.
        
        Args:
            name: Counter name
            value: Value to increment by
        """
        try:
            if name not in self.metrics:
                self.metrics[name] = 0
            self.metrics[name] += value
            
        except Exception as e:
            raise PipelineError(f"Failed to increment counter: {e}")
    
    def record_error(self, error: str) -> None:
        """Record an error.
        
        Args:
            error: Error message
        """
        try:
            self.metrics["errors"] += 1
            self.state["error"] = error
            
        except Exception as e:
            raise PipelineError(f"Failed to record error: {e}")
    
    def record_warning(self, warning: str) -> None:
        """Record a warning.
        
        Args:
            warning: Warning message
        """
        try:
            self.metrics["warnings"] += 1
            
        except Exception as e:
            raise PipelineError(f"Failed to record warning: {e}")
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get metrics.
        
        Returns:
            Dictionary with metrics
        """
        try:
            return {
                "state": self.state,
                "metrics": self.metrics
            }
            
        except Exception as e:
            raise PipelineError(f"Failed to get metrics: {e}")
    
    def save_metrics(self, filename: str = "metrics.json") -> None:
        """Save metrics to a file.
        
        Args:
            filename: Output filename
        """
        if not self.metrics_dir:
            return
            
        try:
            metrics_file = self.metrics_dir / filename
            metrics = self.get_metrics()
            
            with open(metrics_file, 'w') as f:
                json.dump(metrics, f, indent=2)
                
        except Exception as e:
            raise PipelineError(f"Failed to save metrics: {e}")
    
    def __str__(self) -> str:
        """Get string representation.
        
        Returns:
            String representation
        """
        try:
            metrics = self.get_metrics()
            return json.dumps(metrics, indent=2)
            
        except Exception as e:
            return f"Failed to get string representation: {e}" 