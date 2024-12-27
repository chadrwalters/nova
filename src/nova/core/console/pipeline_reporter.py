"""Pipeline reporting and progress tracking."""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Union

from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from nova.core.console.color_scheme import ColorScheme
from nova.core.console.logger import ConsoleLogger
from nova.core.error.error_tracker import ErrorTracker
from nova.core.utils.metrics import MetricsTracker, MetricType
from nova.core.utils.timing import TimingManager


@dataclass
class PipelineStats:
    """Statistics for the entire pipeline."""
    total_phases: int = 0
    completed_phases: int = 0
    current_phase: Optional[str] = None
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
    phase_timings: Dict[str, float] = field(default_factory=dict)
    operation_timings: Dict[str, float] = field(default_factory=dict)


class PipelineReporter:
    """Manages pipeline-level reporting and statistics."""
    
    def __init__(
        self,
        logger: ConsoleLogger,
        color_scheme: Optional[ColorScheme] = None,
        metrics_dir: Optional[Union[str, Path]] = None
    ):
        """Initialize pipeline reporter.
        
        Args:
            logger: Console logger instance
            color_scheme: Optional color scheme to use
            metrics_dir: Optional directory for metrics storage
        """
        self.logger = logger
        self.color_scheme = color_scheme or ColorScheme()
        self.stats = PipelineStats()
        self.error_tracker = ErrorTracker()
        self._progress = None
        
        # Initialize metrics and timing
        self.metrics = MetricsTracker(metrics_dir=metrics_dir)
        self.timing = TimingManager(metrics_tracker=self.metrics, console=self.logger.console)
        
    def start_pipeline(self, total_phases: int) -> None:
        """Start pipeline execution.
        
        Args:
            total_phases: Total number of phases to execute
        """
        self.stats = PipelineStats()
        self.stats.start_time = datetime.now()
        self.stats.total_phases = total_phases
        
        # Start pipeline timer
        self.timing.start_timer(
            "pipeline_execution",
            metadata={"total_phases": str(total_phases)}
        )
        
        # Initialize metrics
        self.metrics.gauge("pipeline_total_phases", total_phases)
        
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
        self.logger.info("Starting pipeline execution")
        
    def start_phase(self, phase_name: str, total_files: int = 0) -> None:
        """Start a new pipeline phase.
        
        Args:
            phase_name: Name of the phase
            total_files: Expected total number of files
        """
        self.stats.current_phase = phase_name
        self.stats.total_files += total_files
        
        # Start phase timer
        self.timing.start_timer(
            f"phase_{phase_name}",
            parent="pipeline_execution",
            metadata={"total_files": str(total_files)}
        )
        
        # Initialize phase metrics
        self.metrics.gauge(f"phase_{phase_name}_total_files", total_files)
        
        self.logger.info(f"\nStarting phase: {phase_name}")
        self.logger.info(f"Files to process: {total_files}")
        
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
        if not self.stats.current_phase:
            raise RuntimeError("No phase currently running")
            
        self.timing.start_timer(
            operation,
            parent=f"phase_{self.stats.current_phase}",
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
        """Update pipeline progress.
        
        Args:
            files_processed: Number of files processed
            bytes_processed: Number of bytes processed
            successful: Whether processing was successful
            error_type: Type of error if unsuccessful
            custom_metrics: Optional custom metrics to track
            file_info: Optional information about the processed file
        """
        # Update stats
        self.stats.processed_files += files_processed
        self.stats.processed_bytes += bytes_processed
        
        if successful:
            self.stats.successful_files += files_processed
            self.metrics.increment("pipeline_successful_files", files_processed)
        else:
            self.stats.failed_files += files_processed
            if error_type:
                self.stats.error_counts[error_type] = self.stats.error_counts.get(error_type, 0) + 1
                self.metrics.error(f"pipeline_error_{error_type}")
                
        # Update metrics
        self.metrics.gauge("pipeline_processed_files", self.stats.processed_files)
        self.metrics.gauge("pipeline_processed_bytes", self.stats.processed_bytes)
        self.metrics.rate("pipeline_processing_rate", files_processed)
        
        if custom_metrics:
            self.stats.custom_metrics.update(custom_metrics)
            for name, value in custom_metrics.items():
                self.metrics.gauge(f"pipeline_custom_{name}", float(value))
                
        if file_info:
            labels = {"phase": self.stats.current_phase or "unknown"}
            labels.update(file_info)
            self.metrics.increment("files_processed", 1, labels=labels)
            
        # Update progress display
        if self._progress:
            progress_pct = (self.stats.processed_files / self.stats.total_files * 100
                          if self.stats.total_files > 0 else 0)
            phase_pct = (self.stats.completed_phases / self.stats.total_phases * 100
                        if self.stats.total_phases > 0 else 0)
            status = "SUCCESS" if successful else f"ERROR: {error_type}"
            
            self._progress.update(
                0,
                description=f"Pipeline: {phase_pct:.1f}% - Phase {self.stats.current_phase}: "
                          f"{progress_pct:.1f}% - {status} - {self.stats.processed_files} files"
            )
            
    def end_phase(self, phase_name: str) -> None:
        """End a pipeline phase.
        
        Args:
            phase_name: Name of the phase to end
        """
        if phase_name != self.stats.current_phase:
            raise ValueError(f"Cannot end phase {phase_name}, current phase is {self.stats.current_phase}")
            
        # Stop phase timer
        phase_duration = self.timing.stop_timer(f"phase_{phase_name}")
        self.stats.phase_timings[phase_name] = phase_duration
        
        # Update phase completion
        self.stats.completed_phases += 1
        self.metrics.gauge("pipeline_completed_phases", self.stats.completed_phases)
        
        # Log phase summary
        self.logger.info(f"\nPhase {phase_name} completed:")
        self.logger.info(f"Duration: {phase_duration:.2f}s")
        
        self.stats.current_phase = None
        
    def end_pipeline(self) -> None:
        """End pipeline execution."""
        self.stats.end_time = datetime.now()
        
        # Stop pipeline timer
        pipeline_duration = self.timing.stop_timer("pipeline_execution")
        
        # Calculate final metrics
        if self.stats.start_time and self.stats.end_time:
            processing_time = (self.stats.end_time - self.stats.start_time).total_seconds()
            if processing_time > 0:
                files_per_second = self.stats.processed_files / processing_time
                bytes_per_second = self.stats.processed_bytes / processing_time
                
                self.metrics.gauge("pipeline_duration", pipeline_duration)
                self.metrics.gauge("pipeline_files_per_second", files_per_second)
                self.metrics.gauge("pipeline_bytes_per_second", bytes_per_second)
                
        # Create summary table
        table = Table(
            title="Pipeline Execution Summary",
            title_style=self.color_scheme.get_style("title"),
            header_style=self.color_scheme.get_style("header"),
            border_style=self.color_scheme.get_style("border")
        )
        
        table.add_column("Metric", style="bold")
        table.add_column("Value")
        
        table.add_row("Total Phases", str(self.stats.total_phases))
        table.add_row("Completed Phases", str(self.stats.completed_phases))
        table.add_row("Total Files", str(self.stats.total_files))
        table.add_row("Processed Files", str(self.stats.processed_files))
        table.add_row("Successful Files", str(self.stats.successful_files))
        table.add_row("Failed Files", str(self.stats.failed_files))
        table.add_row("Total Bytes", f"{self.stats.total_bytes / 1024 / 1024:.1f} MB")
        table.add_row("Processed Bytes", f"{self.stats.processed_bytes / 1024 / 1024:.1f} MB")
        table.add_row("Duration", f"{pipeline_duration:.2f}s")
        
        if self.stats.error_counts:
            table.add_section()
            table.add_row("Error Type", "Count", style="bold red")
            for error_type, count in self.stats.error_counts.items():
                table.add_row(error_type, str(count), style="red")
                
        if self.stats.custom_metrics:
            table.add_section()
            table.add_row("Custom Metric", "Value", style="bold cyan")
            for name, value in self.stats.custom_metrics.items():
                table.add_row(name, str(value), style="cyan")
                
        self.logger.console.print("\n")
        self.logger.console.print(table)
        
        # Display timing summary
        self.timing.display_summary()
        
        # Save metrics
        self.metrics.save_metrics("pipeline_metrics.json")
        
        # Clean up
        if self._progress:
            self._progress.stop()
            self._progress = None
            
    def get_statistics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        metric_types: Optional[List[MetricType]] = None
    ) -> Dict[str, Dict[str, float]]:
        """Get pipeline statistics with optional filtering."""
        return self.metrics.get_statistics(
            start_time=start_time,
            end_time=end_time,
            metric_types=metric_types
        ) 