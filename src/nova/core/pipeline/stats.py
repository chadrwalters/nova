"""Pipeline phase statistics."""
from typing import Dict, Any, List, Optional
from datetime import datetime


class PhaseStats:
    """Phase statistics."""

    def __init__(self, phase_name: str, total_files: int = 0) -> None:
        """Initialize phase statistics.
        
        Args:
            phase_name: Phase name
            total_files: Total number of files
        """
        self.phase_name = phase_name
        self.total_files = total_files
        self.processed_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.metrics: Dict[str, Any] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        self._data: Dict[str, Any] = {}

    def start(self) -> None:
        """Start phase processing."""
        self.start_time = datetime.now()

    def end(self) -> None:
        """End phase processing."""
        self.end_time = datetime.now()

    def get_duration(self) -> float:
        """Get phase duration in seconds.
        
        Returns:
            Duration in seconds
        """
        if not self.start_time or not self.end_time:
            return 0.0
        return (self.end_time - self.start_time).total_seconds()

    def get_stats(self) -> Dict[str, Any]:
        """Get phase statistics.
        
        Returns:
            Dictionary containing phase statistics
        """
        return {
            "phase_name": self.phase_name,
            "total_files": self.total_files,
            "processed_files": self.processed_files,
            "failed_files": self.failed_files,
            "skipped_files": self.skipped_files,
            "duration": self.get_duration(),
            "errors": len(self.errors),
            "warnings": len(self.warnings),
            "progress": self.get_progress(),
            "metrics": self.metrics,
            "start_time": self.start_time,
            "end_time": self.end_time
        }

    def add_error(self, error: str) -> None:
        """Add error message.
        
        Args:
            error: Error message
        """
        self.errors.append(error)

    def add_warning(self, warning: str) -> None:
        """Add warning message.
        
        Args:
            warning: Warning message
        """
        self.warnings.append(warning)

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update phase metrics.
        
        Args:
            metrics: Dictionary of metrics
        """
        self.metrics.update(metrics)

    def set_data(self, key: str, value: Any) -> None:
        """Set phase data.
        
        Args:
            key: Data key
            value: Data value
        """
        self._data[key] = value

    def get_data(self, key: str) -> Any:
        """Get phase data.
        
        Args:
            key: Data key
            
        Returns:
            Data value
        """
        return self._data.get(key)

    def get_progress(self) -> float:
        """Get phase progress percentage.
        
        Returns:
            Progress percentage between 0 and 100
        """
        if self.total_files == 0:
            return 100.0
        return (self.processed_files + self.failed_files + self.skipped_files) / self.total_files * 100 