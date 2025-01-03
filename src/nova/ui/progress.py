"""Enhanced progress visualization for Nova."""
from typing import Dict, List, Optional
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress,
    SpinnerColumn,
    BarColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
    TaskProgressColumn,
)
from rich.layout import Layout

from nova.core.progress import ProcessingStatus, PhaseProgress, FileProgress


class ProgressDisplay:
    """Enhanced progress display for Nova pipeline."""
    
    def __init__(self):
        """Initialize progress display."""
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            TimeRemainingColumn(),
        )
        self.layout = Layout()
        self._setup_layout()
        
    def _setup_layout(self) -> None:
        """Set up the layout structure."""
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="body"),
            Layout(name="footer", size=3),
        )
        
        # Split body into progress and stats
        self.layout["body"].split_row(
            Layout(name="progress", ratio=2),
            Layout(name="stats", ratio=1),
        )
        
    def create_phase_progress(self, phase: str, total: int) -> int:
        """Create a progress bar for a phase.
        
        Args:
            phase: Phase name
            total: Total number of files
            
        Returns:
            Task ID for the progress bar
        """
        return self.progress.add_task(f"[cyan]{phase.upper()}[/cyan]", total=total)
        
    def create_stats_table(self, phase_progress: Dict[str, PhaseProgress]) -> Table:
        """Create statistics table.
        
        Args:
            phase_progress: Dictionary of phase progress
            
        Returns:
            Rich Table object
        """
        table = Table(title="Processing Statistics")
        table.add_column("Phase", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Progress", justify="right")
        table.add_column("Duration", justify="right")
        
        for phase, progress in phase_progress.items():
            # Calculate progress percentage
            if progress.total_files > 0:
                percentage = (progress.completed_files / progress.total_files) * 100
            else:
                percentage = 0
                
            # Format duration
            duration = progress.duration if progress.duration is not None else 0
            
            # Add row with appropriate status color
            status_style = {
                ProcessingStatus.PENDING: "white",
                ProcessingStatus.IN_PROGRESS: "yellow",
                ProcessingStatus.COMPLETED: "green",
                ProcessingStatus.FAILED: "red"
            }[progress.status]
            
            table.add_row(
                phase.upper(),
                f"[{status_style}]{progress.status.value}[/{status_style}]",
                f"{percentage:.1f}%",
                f"{duration:.1f}s"
            )
            
        return table
        
    def create_file_table(self, current_files: Dict[str, List[FileProgress]]) -> Table:
        """Create table of current file processing status.
        
        Args:
            current_files: Dictionary of current files being processed per phase
            
        Returns:
            Rich Table object
        """
        table = Table(title="Current Processing")
        table.add_column("Phase", style="cyan")
        table.add_column("File")
        table.add_column("Status", justify="center")
        table.add_column("Duration", justify="right")
        
        for phase, files in current_files.items():
            for file in files:
                # Format duration
                duration = file.duration if file.duration is not None else 0
                
                # Add row with appropriate status color
                status_style = {
                    ProcessingStatus.PENDING: "white",
                    ProcessingStatus.IN_PROGRESS: "yellow",
                    ProcessingStatus.COMPLETED: "green",
                    ProcessingStatus.FAILED: "red"
                }[file.status]
                
                table.add_row(
                    phase.upper(),
                    file.file_path.name,
                    f"[{status_style}]{file.status.value}[/{status_style}]",
                    f"{duration:.1f}s"
                )
                
        return table
        
    def update_display(
        self,
        phase_progress: Dict[str, PhaseProgress],
        current_files: Dict[str, List[FileProgress]],
        task_id: int,
        completed: int
    ) -> None:
        """Update the display with current progress.
        
        Args:
            phase_progress: Dictionary of phase progress
            current_files: Dictionary of current files being processed per phase
            task_id: Task ID of the current progress bar
            completed: Number of completed files
        """
        # Update progress bar
        self.progress.update(task_id, completed=completed)
        
        # Update statistics
        stats_table = self.create_stats_table(phase_progress)
        self.layout["stats"].update(Panel(stats_table))
        
        # Update current files
        files_table = self.create_file_table(current_files)
        self.layout["progress"].update(Panel(files_table))
        
    def start(self) -> None:
        """Start the live display."""
        self.progress.start()
        
    def stop(self) -> None:
        """Stop the live display."""
        self.progress.stop()
        
    def print_summary(self, phase_progress: Dict[str, PhaseProgress]) -> None:
        """Print final processing summary.
        
        Args:
            phase_progress: Dictionary of phase progress
        """
        table = Table(title="Processing Summary")
        table.add_column("Phase", style="cyan")
        table.add_column("Files", justify="right")
        table.add_column("Success", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Duration", justify="right")
        
        total_files = 0
        total_success = 0
        total_failed = 0
        total_duration = 0.0
        
        for phase, progress in phase_progress.items():
            duration = progress.duration if progress.duration is not None else 0
            table.add_row(
                phase.upper(),
                str(progress.total_files),
                str(progress.completed_files),
                str(progress.failed_files),
                f"{duration:.1f}s"
            )
            
            total_files += progress.total_files
            total_success += progress.completed_files
            total_failed += progress.failed_files
            total_duration += duration
            
        # Add totals row
        table.add_row(
            "TOTAL",
            str(total_files),
            str(total_success),
            str(total_failed),
            f"{total_duration:.1f}s",
            style="bold"
        )
        
        self.console.print("\n")
        self.console.print(table)
        
        # Print status message
        if total_failed == 0:
            self.console.print("\n[green]All files processed successfully![/green]")
        else:
            self.console.print(f"\n[red]Processing completed with {total_failed} failures.[/red]") 