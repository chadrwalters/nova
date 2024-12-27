"""Pipeline execution reporting."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn, BarColumn

from nova.core.utils.timing import TimingManager
from nova.core.utils.metrics import MetricsTracker
from nova.core.utils.error_tracker import ErrorTracker
from nova.core.console.logger import ConsoleLogger
from nova.core.console.color_scheme import ColorScheme


@dataclass
class PipelineStats:
    """Pipeline execution statistics."""
    
    total_phases: int = 0
    completed_phases: int = 0
    current_phase: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    phase_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    error_counts: Dict[str, int] = field(default_factory=dict)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    
    def __getitem__(self, key: str) -> Any:
        """Get item by key.
        
        Args:
            key: Key to get
            
        Returns:
            Value for key
            
        Raises:
            KeyError: If key not found
        """
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)
        
    def __setitem__(self, key: str, value: Any) -> None:
        """Set item by key.
        
        Args:
            key: Key to set
            value: Value to set
            
        Raises:
            AttributeError: If key cannot be set
        """
        if hasattr(self, key):
            setattr(self, key, value)
        else:
            raise AttributeError(f"Cannot set {key}")
            
    def __contains__(self, key: str) -> bool:
        """Check if key exists.
        
        Args:
            key: Key to check
            
        Returns:
            True if key exists
        """
        return hasattr(self, key)


class PipelineReporter:
    """Generates reports on pipeline execution."""
    
    def __init__(
        self,
        logger: Optional[ConsoleLogger] = None,
        color_scheme: Optional[ColorScheme] = None,
        timing: Optional[TimingManager] = None,
        metrics: Optional[MetricsTracker] = None,
        console: Optional[Console] = None
    ):
        """Initialize pipeline reporter.
        
        Args:
            logger: Optional console logger instance
            color_scheme: Optional color scheme instance
            timing: Optional timing manager instance
            metrics: Optional metrics tracker instance
            console: Optional rich console instance
        """
        self.logger = logger or ConsoleLogger(console=console)
        self.color_scheme = color_scheme or ColorScheme()
        self.timing = timing or TimingManager()
        self.metrics = metrics or MetricsTracker()
        self.console = console or self.logger.console
        
        # Initialize state
        self.state = PipelineStats()
        
        # Initialize progress display
        self._progress = None
        self._pipeline_task = None
        self._phase_task = None
        
    def start_pipeline(self, total_phases: int) -> None:
        """Start pipeline execution tracking.
        
        Args:
            total_phases: Total number of phases to execute
        """
        self.state.start_time = datetime.now()
        self.state.total_phases = total_phases
        self.state.completed_phases = 0
        self.state.phase_stats = {}
        
        # Start pipeline timer
        self.timing.start_timer("pipeline_execution")
        
        # Initialize metrics
        self.metrics.set_gauge("pipeline_total_phases", total_phases)
        
        # Create progress bar
        self._progress = Progress(
            SpinnerColumn(style=self.color_scheme.get_style("spinner")),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
            TimeElapsedColumn(),
            console=self.console,
            auto_refresh=False,
            expand=True
        )
        
        self._progress.start()
        self._pipeline_task = self._progress.add_task(
            description="Pipeline: Starting...",
            total=total_phases
        )
        self._phase_task = None
        self._progress.refresh()
        
        self.logger.info(f"Starting pipeline execution with {total_phases} phases")
        
    def start_phase(self, phase: Union[str, 'PipelinePhase'], total_files: int = 0) -> None:
        """Start a new pipeline phase.
        
        Args:
            phase: Name of the phase or PipelinePhase object
            total_files: Expected total number of files
        """
        phase_name = phase.name if hasattr(phase, 'name') else str(phase)
        self.state.current_phase = phase_name
        self.state.phase_stats[phase_name] = {
            "start_time": datetime.now(),
            "end_time": None,
            "total_files": total_files,
            "processed_files": 0,
            "successful_files": 0,
            "failed_files": 0,
            "skipped_files": 0,
            "total_bytes": 0,
            "processed_bytes": 0,
            "error_counts": {},
            "custom_metrics": {},
            "operation_timings": {}
        }
        
        # Start phase timer
        self.timing.start_timer(f"phase_{phase_name}")
        
        # Initialize phase metrics
        self.metrics.set_gauge(f"phase_{phase_name}_total_files", total_files)
        
        # Update progress display
        if self._progress:
            if self._phase_task is not None:
                try:
                    self._progress.remove_task(self._phase_task)
                except KeyError:
                    pass
                
            self._phase_task = self._progress.add_task(
                description=f"Phase {phase_name}: Starting...",
                total=total_files if total_files > 0 else 1
            )
            self._progress.refresh()
            
        self.logger.info(f"\nStarting phase: {phase_name}")
        if total_files > 0:
            self.logger.info(f"Files to process: {total_files}")
            
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
        if not self.state.current_phase:
            raise RuntimeError("No phase currently running")
            
        phase_stats = self.state.phase_stats[self.state.current_phase]
        
        # Update stats
        phase_stats['processed_files'] += files_processed
        phase_stats['processed_bytes'] += bytes_processed
        
        if successful:
            phase_stats['successful_files'] += files_processed
            self.metrics.increment("pipeline_successful_files", files_processed)
        else:
            phase_stats['failed_files'] += files_processed
            if error_type:
                phase_stats['error_counts'][error_type] = phase_stats['error_counts'].get(error_type, 0) + 1
                self.metrics.increment(f"pipeline_error_{error_type}")
                
        # Update metrics
        self.metrics.set_gauge("pipeline_processed_files", phase_stats['processed_files'])
        self.metrics.set_gauge("pipeline_processed_bytes", phase_stats['processed_bytes'])
        self.metrics.increment("pipeline_processing_rate", files_processed)
        
        if custom_metrics:
            phase_stats['custom_metrics'].update(custom_metrics)
            for name, value in custom_metrics.items():
                self.metrics.set_gauge(f"pipeline_custom_{name}", float(value))
                
        if file_info:
            self.metrics.add_label("files_processed", file_info)
            self.metrics.increment("files_processed")
            
        # Update progress display
        if self._progress and self._phase_task is not None:
            try:
                self._progress.update(
                    self._phase_task,
                    advance=files_processed,
                    description=f"Phase {self.state.current_phase}: "
                              f"{phase_stats['processed_files']}/{phase_stats['total_files']} files"
                )
                self._progress.refresh()
            except KeyError:
                pass
                
    def end_phase(self, phase_name: str) -> None:
        """End a pipeline phase.
        
        Args:
            phase_name: Name of the phase to end
        """
        if phase_name != self.state.current_phase:
            raise RuntimeError(f"Cannot end phase {phase_name}, current phase is {self.state.current_phase}")
            
        phase_stats = self.state.phase_stats[phase_name]
        phase_stats["end_time"] = datetime.now()
        
        # Set progress to 100%
        if phase_stats['total_files'] == 0:
            phase_stats['total_files'] = 100
            phase_stats['processed_files'] = 100
        else:
            remaining = phase_stats['total_files'] - phase_stats['processed_files']
            if remaining > 0:
                self.update_progress(files_processed=remaining)
        
        # Stop phase timer
        duration = self.timing.stop_timer(f"phase_{phase_name}")
        phase_stats["duration"] = duration
        
        # Update state
        self.state.completed_phases += 1
        self.state.current_phase = None
        
        # Update progress
        if self._progress:
            if self._pipeline_task is not None:
                try:
                    self._progress.update(
                        self._pipeline_task,
                        advance=1,
                        description=f"Pipeline: {self.state.completed_phases}/{self.state.total_phases} phases"
                    )
                except KeyError:
                    pass
                
            if self._phase_task is not None:
                try:
                    self._progress.remove_task(self._phase_task)
                except KeyError:
                    pass
                self._phase_task = None
                
            self._progress.refresh()
            
        # Log phase completion
        self.logger.info(f"\nPhase {phase_name} completed:")
        self.logger.info(f"Duration: {duration:.2f}s")
        self.logger.info(f"Files processed: {phase_stats['processed_files']}/{phase_stats['total_files']}")
        self.logger.info(f"Files successful: {phase_stats['successful_files']}")
        self.logger.info(f"Files failed: {phase_stats['failed_files']}")
        self.logger.info(f"Files skipped: {phase_stats['skipped_files']}")
        
        if phase_stats["error_counts"]:
            self.logger.info("\nErrors by type:")
            for error_type, count in phase_stats["error_counts"].items():
                self.logger.info(f"  {error_type}: {count}")
                
    def end_pipeline(self) -> None:
        """End pipeline execution tracking."""
        self.state.end_time = datetime.now()
        
        # Stop pipeline timer
        duration = self.timing.stop_timer("pipeline_execution")
        
        # Stop progress display
        if self._progress:
            self._progress.stop()
            
        # Log pipeline completion
        self.logger.info("\nPipeline execution completed:")
        self.logger.info(f"Duration: {duration:.2f}s")
        self.logger.info(f"Phases completed: {self.state.completed_phases}/{self.state.total_phases}")
        
        total_files = sum(stats["total_files"] for stats in self.state.phase_stats.values())
        processed_files = sum(stats["processed_files"] for stats in self.state.phase_stats.values())
        successful_files = sum(stats["successful_files"] for stats in self.state.phase_stats.values())
        failed_files = sum(stats["failed_files"] for stats in self.state.phase_stats.values())
        skipped_files = sum(stats["skipped_files"] for stats in self.state.phase_stats.values())
        
        self.logger.info(f"Total files: {total_files}")
        self.logger.info(f"Files processed: {processed_files}")
        self.logger.info(f"Files successful: {successful_files}")
        self.logger.info(f"Files failed: {failed_files}")
        self.logger.info(f"Files skipped: {skipped_files}")
        
        if self.state.error_counts:
            self.logger.info("\nTotal errors by type:")
            for error_type, count in self.state.error_counts.items():
                self.logger.info(f"  {error_type}: {count}")
                
    def start_operation(self, operation_name: str) -> None:
        """Start timing an operation.
        
        Args:
            operation_name: Name of the operation
        """
        self.timing.start_timer(operation_name)
        
    def end_operation(self, operation_name: str) -> None:
        """End timing an operation.
        
        Args:
            operation_name: Name of the operation
        """
        duration = self.timing.stop_timer(operation_name)
        if self.state.current_phase:
            phase_stats = self.state.phase_stats[self.state.current_phase]
            phase_stats["operation_timings"][operation_name] = duration 

    def get_phase_progress(self, phase_name: str) -> int:
        """Get the progress percentage of a phase.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Progress percentage (0-100)
        """
        if phase_name not in self.state.phase_stats:
            return 0
            
        phase_stats = self.state.phase_stats[phase_name]
        total = phase_stats['total_files']
        if total == 0:
            return 100 if phase_stats.get('end_time') else 0
            
        processed = phase_stats['processed_files']
        return min(100, int((processed / total) * 100))

    def update_phase_progress(self, phase_name: str, progress: int) -> None:
        """Update the progress of a phase.
        
        Args:
            phase_name: Name of the phase
            progress: Progress percentage (0-100)
        """
        if phase_name not in self.state.phase_stats:
            raise RuntimeError(f"Phase {phase_name} not started")
            
        phase_stats = self.state.phase_stats[phase_name]
        
        # If no files to process, just update processed_files to track percentage
        if phase_stats['total_files'] == 0:
            phase_stats['total_files'] = 100
            phase_stats['processed_files'] = progress
        else:
            # Calculate how many files to process to reach the target percentage
            target_processed = int((progress / 100) * phase_stats['total_files'])
            current_processed = phase_stats['processed_files']
            files_to_process = target_processed - current_processed
            
            if files_to_process > 0:
                self.update_progress(files_processed=files_to_process) 

    def complete_phase(self, phase_name: str) -> None:
        """Alias for end_phase for backward compatibility.
        
        Args:
            phase_name: Name of the phase to complete
        """
        self.end_phase(phase_name) 