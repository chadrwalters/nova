"""Pipeline reporter for monitoring and reporting pipeline progress."""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class PhaseStats:
    """Statistics for a pipeline phase."""
    phase_name: str
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    total_files: int = 0
    processed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    errors: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)

    @property
    def duration(self) -> Optional[float]:
        """Get phase duration in seconds."""
        if not self.start_time or not self.end_time:
            return None
        return (self.end_time - self.start_time).total_seconds()

    @property
    def success_rate(self) -> float:
        """Get success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.processed_files / self.total_files) * 100

    @property
    def failure_rate(self) -> float:
        """Get failure rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.failed_files / self.total_files) * 100

    @property
    def skip_rate(self) -> float:
        """Get skip rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.skipped_files / self.total_files) * 100


class PipelineReporter:
    """Reporter for pipeline progress and metrics."""

    def __init__(self):
        """Initialize pipeline reporter."""
        self.logger = logging.getLogger(__name__)
        self._phase_stats: Dict[str, PhaseStats] = {}
        self._current_phase: Optional[str] = None
        self._start_time: Optional[datetime] = None
        self._end_time: Optional[datetime] = None

    def start_pipeline(self) -> None:
        """Start pipeline reporting."""
        self._start_time = datetime.now()
        self.logger.info("Started pipeline execution")

    def end_pipeline(self) -> None:
        """End pipeline reporting."""
        self._end_time = datetime.now()
        duration = self.total_duration
        if duration is not None:
            self.logger.info(f"Pipeline execution completed in {duration:.2f} seconds")
        else:
            self.logger.info("Pipeline execution completed")

    def start_phase(self, phase_name: str) -> None:
        """Start monitoring a phase.
        
        Args:
            phase_name: Name of the phase
        """
        if phase_name not in self._phase_stats:
            self._phase_stats[phase_name] = PhaseStats(phase_name=phase_name)
        
        self._current_phase = phase_name
        self._phase_stats[phase_name].start_time = datetime.now()
        self.logger.info(f"Started phase: {phase_name}")

    def end_phase(self, phase_name: str) -> None:
        """End monitoring a phase.
        
        Args:
            phase_name: Name of the phase
        """
        if phase_name not in self._phase_stats:
            raise ValueError(f"Phase not found: {phase_name}")
            
        self._phase_stats[phase_name].end_time = datetime.now()
        if self._current_phase == phase_name:
            self._current_phase = None
            
        duration = self._phase_stats[phase_name].duration
        if duration is not None:
            self.logger.info(f"Completed phase {phase_name} in {duration:.2f} seconds")
        else:
            self.logger.info(f"Completed phase {phase_name}")

    def update_progress(self, phase_name: str, total_files: Optional[int] = None,
                       processed_files: Optional[int] = None,
                       failed_files: Optional[int] = None,
                       skipped_files: Optional[int] = None) -> None:
        """Update progress for a phase.
        
        Args:
            phase_name: Name of the phase
            total_files: Total number of files
            processed_files: Number of processed files
            failed_files: Number of failed files
            skipped_files: Number of skipped files
        """
        if phase_name not in self._phase_stats:
            self._phase_stats[phase_name] = PhaseStats(phase_name=phase_name)
            
        stats = self._phase_stats[phase_name]
        
        if total_files is not None:
            stats.total_files = total_files
        if processed_files is not None:
            stats.processed_files = processed_files
        if failed_files is not None:
            stats.failed_files = failed_files
        if skipped_files is not None:
            stats.skipped_files = skipped_files
            
        self.logger.debug(
            f"Phase {phase_name} progress: "
            f"{stats.processed_files}/{stats.total_files} files processed, "
            f"{stats.failed_files} failed, {stats.skipped_files} skipped"
        )

    def add_phase_stats(self, phase_name: str, metrics: Dict[str, Any]) -> None:
        """Add metrics for a phase.
        
        Args:
            phase_name: Name of the phase
            metrics: Dictionary of metrics
        """
        if phase_name not in self._phase_stats:
            self._phase_stats[phase_name] = PhaseStats(phase_name=phase_name)
            
        self._phase_stats[phase_name].metrics.update(metrics)

    def get_phase_stats(self, phase_name: str) -> PhaseStats:
        """Get statistics for a phase.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Phase statistics
            
        Raises:
            ValueError: If phase not found
        """
        if phase_name not in self._phase_stats:
            raise ValueError(f"Phase not found: {phase_name}")
            
        return self._phase_stats[phase_name]

    def get_all_stats(self) -> Dict[str, PhaseStats]:
        """Get statistics for all phases.
        
        Returns:
            Dictionary of phase statistics
        """
        return self._phase_stats

    @property
    def total_duration(self) -> Optional[float]:
        """Get total pipeline duration in seconds."""
        if not self._start_time or not self._end_time:
            return None
        return (self._end_time - self._start_time).total_seconds()

    @property
    def current_phase(self) -> Optional[str]:
        """Get name of current phase."""
        return self._current_phase

    @property
    def total_files(self) -> int:
        """Get total number of files across all phases."""
        return sum(stats.total_files for stats in self._phase_stats.values())

    @property
    def total_processed(self) -> int:
        """Get total number of processed files across all phases."""
        return sum(stats.processed_files for stats in self._phase_stats.values())

    @property
    def total_failed(self) -> int:
        """Get total number of failed files across all phases."""
        return sum(stats.failed_files for stats in self._phase_stats.values())

    @property
    def total_skipped(self) -> int:
        """Get total number of skipped files across all phases."""
        return sum(stats.skipped_files for stats in self._phase_stats.values())

    @property
    def total_errors(self) -> int:
        """Get total number of errors across all phases."""
        return sum(stats.errors for stats in self._phase_stats.values())

    @property
    def overall_success_rate(self) -> float:
        """Get overall success rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.total_processed / self.total_files) * 100

    @property
    def overall_failure_rate(self) -> float:
        """Get overall failure rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.total_failed / self.total_files) * 100

    @property
    def overall_skip_rate(self) -> float:
        """Get overall skip rate as percentage."""
        if self.total_files == 0:
            return 0.0
        return (self.total_skipped / self.total_files) * 100 