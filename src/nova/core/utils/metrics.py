"""Metrics tracking utilities."""

from typing import Dict, Any, Optional
from datetime import datetime
import logging
from pydantic import BaseModel, Field, ConfigDict

class MetricsTracker(BaseModel):
    """Tracks metrics for processing operations."""
    start_time: Optional[datetime] = Field(default=None, description="Operation start time")
    end_time: Optional[datetime] = Field(default=None, description="Operation end time")
    total_files: int = Field(default=0, description="Total files processed")
    successful_files: int = Field(default=0, description="Successfully processed files")
    failed_files: int = Field(default=0, description="Failed files")
    skipped_files: int = Field(default=0, description="Skipped files")
    total_bytes: int = Field(default=0, description="Total bytes processed")
    error_counts: Dict[str, int] = Field(default_factory=dict, description="Error type counts")
    custom_metrics: Dict[str, Any] = Field(default_factory=dict, description="Custom metrics")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

    def start(self) -> None:
        """Start tracking metrics."""
        self.start_time = datetime.now()
        self.reset_counters()

    def stop(self) -> None:
        """Stop tracking metrics."""
        self.end_time = datetime.now()

    def reset_counters(self) -> None:
        """Reset all counters."""
        self.total_files = 0
        self.successful_files = 0
        self.failed_files = 0
        self.skipped_files = 0
        self.total_bytes = 0
        self.error_counts.clear()
        self.custom_metrics.clear()

    def add_success(self, file_size: int = 0) -> None:
        """Record a successful operation.
        
        Args:
            file_size: Size of processed file in bytes
        """
        self.total_files += 1
        self.successful_files += 1
        self.total_bytes += file_size

    def add_failure(self, error_type: str) -> None:
        """Record a failed operation.
        
        Args:
            error_type: Type of error that occurred
        """
        self.total_files += 1
        self.failed_files += 1
        self.error_counts[error_type] = self.error_counts.get(error_type, 0) + 1

    def add_skip(self) -> None:
        """Record a skipped operation."""
        self.total_files += 1
        self.skipped_files += 1

    def add_custom_metric(self, name: str, value: Any) -> None:
        """Add a custom metric.
        
        Args:
            name: Metric name
            value: Metric value
        """
        self.custom_metrics[name] = value

    def get_duration(self) -> Optional[float]:
        """Get operation duration in seconds.
        
        Returns:
            Duration in seconds or None if not stopped
        """
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return None

    def get_summary(self) -> Dict[str, Any]:
        """Get metrics summary.
        
        Returns:
            Dictionary containing metrics summary
        """
        summary = {
            'total_files': self.total_files,
            'successful_files': self.successful_files,
            'failed_files': self.failed_files,
            'skipped_files': self.skipped_files,
            'total_bytes': self.total_bytes,
            'error_counts': self.error_counts,
            'custom_metrics': self.custom_metrics
        }

        duration = self.get_duration()
        if duration is not None:
            summary['duration_seconds'] = duration

        return summary

    def log_summary(self, logger: Optional[logging.Logger] = None) -> None:
        """Log metrics summary.
        
        Args:
            logger: Optional logger instance to use
        """
        if logger is None:
            logger = logging.getLogger(__name__)

        summary = self.get_summary()
        duration = summary.get('duration_seconds')
        
        logger.info("Processing Summary:")
        logger.info(f"Total files: {summary['total_files']}")
        logger.info(f"Successful: {summary['successful_files']}")
        logger.info(f"Failed: {summary['failed_files']}")
        logger.info(f"Skipped: {summary['skipped_files']}")
        logger.info(f"Total bytes: {summary['total_bytes']}")
        
        if duration is not None:
            logger.info(f"Duration: {duration:.2f}s")
        
        if summary['error_counts']:
            logger.info("Error counts:")
            for error_type, count in summary['error_counts'].items():
                logger.info(f"  {error_type}: {count}")
        
        if summary['custom_metrics']:
            logger.info("Custom metrics:")
            for name, value in summary['custom_metrics'].items():
                logger.info(f"  {name}: {value}") 