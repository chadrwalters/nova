"""Pipeline execution reporting."""

from typing import Any, Dict, List, Optional
from pathlib import Path
from datetime import datetime

from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn

from nova.core.utils.timing import TimingManager
from nova.core.utils.metrics import MetricsTracker
from nova.core.console.logger import ConsoleLogger
from nova.core.console.color_scheme import ColorScheme


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
        self.state = {
            'start_time': None,
            'end_time': None,
            'total_phases': 0,
            'completed_phases': 0,
            'phase_stats': {}
        }
        
    def start_pipeline(self, total_phases: int) -> None:
        """Start pipeline execution tracking.
        
        Args:
            total_phases: Total number of phases to execute
        """
        self.state['start_time'] = datetime.now()
        self.state['total_phases'] = total_phases
        self.state['completed_phases'] = 0
        self.state['phase_stats'] = {}
        
        self.logger.info(f"Starting pipeline execution with {total_phases} phases")
        
    def add_phase_stats(self, phase_name: str, stats: Dict[str, Any]) -> None:
        """Add statistics for a completed phase.
        
        Args:
            phase_name: Name of the completed phase
            stats: Phase statistics
        """
        self.state['completed_phases'] += 1
        self.state['phase_stats'][phase_name] = stats
        
        # Log phase completion
        self.logger.info(
            f"Phase {phase_name} completed: {stats['files_processed']}/{stats['total_files']} "
            f"files in {stats['duration']:.2f}s"
        )
        
    def end_pipeline(self) -> None:
        """End pipeline execution and display final report."""
        self.state['end_time'] = datetime.now()
        
        # Calculate total duration
        duration = (self.state['end_time'] - self.state['start_time']).total_seconds()
        
        # Create summary table
        table = Table(
            title="Pipeline Execution Summary",
            title_style=self.color_scheme.get_style("title")
        )
        
        # Add columns
        table.add_column("Metric", style=self.color_scheme.get_style("stats"))
        table.add_column("Value", style=self.color_scheme.get_style("highlight"))
        
        # Add summary rows
        table.add_row("Total Phases", str(self.state['total_phases']))
        table.add_row("Completed Phases", str(self.state['completed_phases']))
        table.add_row("Total Duration", f"{duration:.2f}s")
        
        # Add phase statistics
        if self.state['phase_stats']:
            table.add_section()
            table.add_row("Phase Statistics", "", style=self.color_scheme.get_style("title"))
            
            total_files = 0
            total_processed = 0
            
            for phase_name, stats in self.state['phase_stats'].items():
                table.add_row(
                    f"  {phase_name}",
                    f"{stats['files_processed']}/{stats['total_files']} files in {stats['duration']:.2f}s"
                )
                total_files += stats['total_files']
                total_processed += stats['files_processed']
                
            table.add_section()
            table.add_row(
                "Total Files",
                f"{total_processed}/{total_files} ({(total_processed/total_files*100):.1f}%)"
                if total_files > 0 else "0/0"
            )
        
        # Display summary
        self.console.print()
        self.console.print(table)
        
        # Display timing report if available
        if self.timing.has_data():
            timing_table = self.generate_timing_report()
            self.console.print()
            self.console.print(timing_table)
            
        # Display metrics report if available
        if self.metrics.has_data():
            metrics_table = self.generate_metrics_report()
            self.console.print()
            self.console.print(metrics_table)
            
    def generate_timing_report(self) -> Table:
        """Generate timing report table.
        
        Returns:
            Rich table with timing information
        """
        table = Table(
            title="Pipeline Timing Report",
            title_style=self.color_scheme.get_style("title")
        )
        
        # Add columns
        table.add_column("Operation", style=self.color_scheme.get_style("stats"))
        table.add_column("Total Time", style=self.color_scheme.get_style("highlight"))
        table.add_column("Count", style=self.color_scheme.get_style("info"))
        table.add_column("Average", style=self.color_scheme.get_style("success"))
        table.add_column("Min", style=self.color_scheme.get_style("detail"))
        table.add_column("Max", style=self.color_scheme.get_style("warning"))
        
        # Add timing data
        for operation, stats in self.timing.get_all_stats().items():
            table.add_row(
                operation,
                f"{stats['total']:.2f}s",
                str(stats['count']),
                f"{stats['avg']:.2f}s",
                f"{stats['min']:.2f}s",
                f"{stats['max']:.2f}s"
            )
            
        return table
        
    def generate_metrics_report(self) -> Table:
        """Generate metrics report table.
        
        Returns:
            Rich table with metrics information
        """
        table = Table(
            title="Pipeline Metrics Report",
            title_style=self.color_scheme.get_style("title")
        )
        
        # Add columns
        table.add_column("Metric", style=self.color_scheme.get_style("stats"))
        table.add_column("Value", style=self.color_scheme.get_style("highlight"))
        table.add_column("Type", style=self.color_scheme.get_style("info"))
        
        # Add metrics data
        for metric, value in self.metrics.get_all_metrics().items():
            table.add_row(
                metric,
                str(value),
                self.metrics.get_metric_type(metric).name
            )
            
        return table 