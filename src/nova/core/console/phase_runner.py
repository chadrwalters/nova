"""Phase execution and progress tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from nova.core.console.color_scheme import ColorScheme
from nova.core.console.logger import ConsoleLogger
from nova.core.error_tracker import ErrorTracker
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.timing import TimingManager


@dataclass
class PhaseStats:
    """Statistics for a processing phase."""
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    total_bytes: int = 0
    processed_bytes: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    error_counts: Dict[str, int] = field(default_factory=dict)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    operation_timings: Dict[str, float] = field(default_factory=dict)


class PhaseRunner:
    """Manages execution of processing phases and tracks statistics."""
    
    def __init__(
        self,
        logger: ConsoleLogger,
        color_scheme: Optional[ColorScheme] = None,
        metrics_dir: Optional[Union[str, Path]] = None
    ):
        """Initialize phase runner.
        
        Args:
            logger: Console logger instance
            color_scheme: Optional color scheme to use
            metrics_dir: Optional directory for metrics storage
        """
        self.logger = logger
        self.color_scheme = color_scheme or ColorScheme()
        self.stats = PhaseStats()
        self.error_tracker = ErrorTracker()
        self.current_phase: Optional[str] = None
        self._progress = None
        
        # Initialize metrics and timing
        self.metrics = MetricsTracker()
        self.timing = TimingManager(metrics_tracker=self.metrics, console=self.logger.console)
        
    def start_phase(self, phase_name: str, total_files: int = 0) -> None:
        """Start a new processing phase.
        
        Args:
            phase_name: Name of the phase
            total_files: Expected total number of files
        """
        self.current_phase = phase_name
        self.stats = PhaseStats()
        self.stats.start_time = datetime.now()
        self.stats.total_files = total_files
        
        # Start phase timer
        self.timing.start_timer(
            f"phase_{phase_name}",
            metadata={"total_files": str(total_files)}
        )
        
        # Initialize metrics for this phase
        self.metrics.set_gauge(f"phase_{phase_name}_total_files", total_files)
        
        # Create progress bar
        self._progress = Progress(
            SpinnerColumn(style=self.color_scheme.get_style("spinner")),
            TextColumn(
                "[progress.description]{task.description}",
                style=self.color_scheme.get_style("progress_text")
            ),
            TimeElapsedColumn(),
            console=self.logger.console
        )
        
        self._progress.start()
        self.logger.info(f"Starting phase: {phase_name}")
        
    def start_operation(
        self,
        operation: str,
        metadata: Optional[Dict[str, str]] = None
    ) -> None:
        """Start timing an operation within the current phase.
        
        Args:
            operation: Operation name
            metadata: Optional metadata to associate with timing
        """
        if not self.current_phase:
            raise RuntimeError("No phase currently running")
            
        self.timing.start_timer(
            operation,
            parent=f"phase_{self.current_phase}",
            metadata=metadata
        )
        
    def stop_operation(self, operation: str) -> float:
        """Stop timing an operation.
        
        Args:
            operation: Operation name
            
        Returns:
            Duration in seconds
        """
        duration = self.timing.stop_timer(operation)
        self.stats.operation_timings[operation] = duration
        return duration
        
    def update_progress(
        self,
        files_processed: int = 0,
        bytes_processed: int = 0,
        successful: bool = True,
        error_type: Optional[str] = None,
        custom_metrics: Optional[Dict[str, Any]] = None,
        file_info: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update phase progress.
        
        Args:
            files_processed: Number of files processed
            bytes_processed: Number of bytes processed
            successful: Whether processing was successful
            error_type: Type of error if unsuccessful
            custom_metrics: Optional custom metrics to track
            file_info: Optional information about the processed file
        """
        if not self.current_phase:
            raise RuntimeError("No phase currently running")
            
        # Update stats
        self.stats.processed_files += files_processed
        self.stats.processed_bytes += bytes_processed
        
        if successful:
            self.stats.successful_files += files_processed
            self.metrics.increment(f"phase_{self.current_phase}_successful_files", files_processed)
        else:
            self.stats.failed_files += files_processed
            if error_type:
                self.stats.error_counts[error_type] = self.stats.error_counts.get(error_type, 0) + 1
                self.metrics.increment(f"phase_{self.current_phase}_error_{error_type}")
                
        # Update metrics
        self.metrics.set_gauge(f"phase_{self.current_phase}_processed_files", self.stats.processed_files)
        self.metrics.set_gauge(f"phase_{self.current_phase}_processed_bytes", self.stats.processed_bytes)
        self.metrics.increment(f"phase_{self.current_phase}_processing_rate", files_processed)
        
        if custom_metrics:
            self.stats.custom_metrics.update(custom_metrics)
            for name, value in custom_metrics.items():
                self.metrics.set_gauge(f"phase_{self.current_phase}_custom_{name}", float(value))
                
        if file_info:
            self.metrics.add_label(f"phase_{self.current_phase}_files", file_info)
            self.metrics.increment(f"phase_{self.current_phase}_files")
            
        # Update progress display
        if self._progress:
            progress_pct = (self.stats.processed_files / self.stats.total_files * 100
                          if self.stats.total_files > 0 else 0)
            status = "SUCCESS" if successful else f"ERROR: {error_type}"
            self._progress.update(
                0,
                description=f"Phase {self.current_phase}: {progress_pct:.1f}% - {status} - "
                          f"{self.stats.processed_files} files"
            )
            
    def end_phase(self) -> None:
        """End the current processing phase."""
        if not self.current_phase:
            raise RuntimeError("No phase currently running")
            
        self.stats.end_time = datetime.now()
        
        # Stop phase timer
        phase_duration = self.timing.stop_timer(f"phase_{self.current_phase}")
        
        # Calculate final metrics
        if self.stats.start_time and self.stats.end_time:
            processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            if processing_time > 0:
                files_per_second = self.stats.processed_files / processing_time
                bytes_per_second = self.stats.processed_bytes / processing_time
                
                self.metrics.set_gauge(f"phase_{self.current_phase}_duration", phase_duration)
                self.metrics.set_gauge(f"phase_{self.current_phase}_files_per_second", files_per_second)
                self.metrics.set_gauge(f"phase_{self.current_phase}_bytes_per_second", bytes_per_second)
                
        # Log summary
        self.logger.info(f"\nPhase {self.current_phase} completed:")
        self.logger.info(f"Total files: {self.stats.total_files}")
        self.logger.info(f"Processed: {self.stats.processed_files}")
        self.logger.info(f"Successful: {self.stats.successful_files}")
        self.logger.info(f"Failed: {self.stats.failed_files}")
        self.logger.info(f"Duration: {phase_duration:.2f}s")
        
        if self.stats.error_counts:
            self.logger.info("\nErrors by type:")
            for error_type, count in self.stats.error_counts.items():
                self.logger.info(f"  {error_type}: {count}")
                
        if self.stats.custom_metrics:
            self.logger.info("\nCustom metrics:")
            for name, value in self.stats.custom_metrics.items():
                self.logger.info(f"  {name}: {value}")
                
        # Clean up
        if self._progress:
            self._progress.stop()
            self._progress = None
            
        self.current_phase = None
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get current phase statistics.
        
        Returns:
            Dictionary of phase statistics
        """
        return {
            "metrics": self.metrics.get_metrics(),
            "timings": self.stats.operation_timings,
            "errors": self.stats.error_counts,
            "custom": self.stats.custom_metrics
        } 