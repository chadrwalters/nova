"""Pipeline progress reporting."""

import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from nova.core.pipeline.stats import PhaseStats


class PipelineReporter:
    """Pipeline execution reporter."""

    def __init__(self) -> None:
        """Initialize pipeline reporter."""
        self.stats = PhaseStats("pipeline")
        self.phase_stats: Dict[str, PhaseStats] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

    def start_pipeline(self, total_files: int) -> None:
        """Start pipeline execution.
        
        Args:
            total_files: Total number of files to process
        """
        print(f"Starting pipeline execution with {total_files} phases")
        self.stats.total_files = total_files
        self.start_time = datetime.now()
        self.stats.start()

    def update_progress(self, processed_files: int, failed_files: int = 0, skipped_files: int = 0) -> None:
        """Update pipeline progress.
        
        Args:
            processed_files: Number of processed files
            failed_files: Number of failed files
            skipped_files: Number of skipped files
        """
        self.stats.processed_files = processed_files
        self.stats.failed_files = failed_files
        self.stats.skipped_files = skipped_files

    def add_phase_stats(self, phase_name: str, stats: PhaseStats) -> None:
        """Add phase statistics.
        
        Args:
            phase_name: Phase name
            stats: Phase statistics
        """
        self.phase_stats[phase_name] = stats

    def end_pipeline(self) -> None:
        """End pipeline execution."""
        self.end_time = datetime.now()
        self.stats.end()

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics.
        
        Returns:
            Dictionary containing pipeline statistics
        """
        duration = 0.0
        if self.start_time and self.end_time:
            duration = (self.end_time - self.start_time).total_seconds()

        return {
            "total_files": self.stats.total_files,
            "processed_files": self.stats.processed_files,
            "failed_files": self.stats.failed_files,
            "skipped_files": self.stats.skipped_files,
            "duration": duration,
            "phases": {
                name: stats.get_stats() for name, stats in self.phase_stats.items()
            }
        }

    def print_summary(self) -> None:
        """Print pipeline execution summary."""
        stats = self.get_stats()
        print("\nPipeline Execution Summary:")
        print(f"Total files: {stats['total_files']}")
        print(f"Processed files: {stats['processed_files']}")
        print(f"Failed files: {stats['failed_files']}")
        print(f"Skipped files: {stats['skipped_files']}")
        print(f"Duration: {stats['duration']:.2f} seconds")
        print("\nPhase Statistics:")
        for name, phase_stats in stats["phases"].items():
            print(f"\n{name}:")
            print(f"  Processed: {phase_stats['processed_files']}")
            print(f"  Failed: {phase_stats['failed_files']}")
            print(f"  Skipped: {phase_stats['skipped_files']}")
            print(f"  Duration: {phase_stats['duration']:.2f} seconds")
            if phase_stats["errors"]:
                print(f"  Errors: {phase_stats['errors']}")
            if phase_stats["warnings"]:
                print(f"  Warnings: {phase_stats['warnings']}") 