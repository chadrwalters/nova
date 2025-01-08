"""Progress tracking UI components."""
import asyncio
import logging
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.console import Console
from rich.panel import Panel
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
)
from rich.table import Table

from nova.context_processor.core.progress import FileProgress, PhaseProgress, ProgressStatus

logger = logging.getLogger(__name__)


class ProgressDisplay:
    """Display progress of pipeline execution."""

    def __init__(self) -> None:
        """Initialize progress display."""
        self.console = Console()
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold cyan]{task.description:>12}[/]"),
            BarColumn(bar_width=40, style="cyan", complete_style="green"),
            TaskProgressColumn(),
            TextColumn("[dim]{task.completed}/{task.total}[/]"),
            console=self.console,
            expand=False,
            transient=False,  # Make progress display persistent
            refresh_per_second=2,  # Increase refresh rate slightly
        )
        self.progress.start()
        self.task_ids: Dict[str, int] = {}

    def add_phase(self, phase: str, total_files: int) -> int:
        """Add a phase to the progress display.

        Args:
            phase: Phase name
            total_files: Total number of files to process

        Returns:
            Task ID for the phase
        """
        task_id: int = self.progress.add_task(
            f"[cyan]{phase.upper()}[/cyan]",
            total=total_files,
            start=True,
            visible=True,
        )
        self.task_ids[phase] = task_id
        return task_id

    def update_phase(self, phase: str, progress: PhaseProgress) -> None:
        """Update phase progress.

        Args:
            phase: Phase name
            progress: Phase progress data
        """
        if phase in self.task_ids:
            task_id = self.task_ids[phase]
            if progress.files_total > 0:
                percentage = (progress.files_processed / progress.files_total) * 100
                self.progress.update(
                    task_id,
                    completed=progress.files_processed,
                    description=f"{phase.upper():>12}",
                    visible=True,
                )

    def stop(self) -> None:
        """Stop progress display."""
        self.progress.stop()

    def __enter__(self) -> "ProgressDisplay":
        """Enter context manager."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context manager."""
        self.stop()

    async def print_summary(
        self,
        phases: Dict[str, PhaseProgress],
        files: Dict[Path, FileProgress],
    ) -> None:
        """Print processing summary.

        Args:
            phases: Phase progress data
            files: File progress data
        """
        # Stop the progress display before showing summary
        self.stop()

        # Create summary table
        table = Table(title="Processing Summary")
        table.add_column("Phase", style="cyan")
        table.add_column("Total", justify="right")
        table.add_column("Completed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Progress", justify="right")
        table.add_column("Duration", justify="right")

        all_successful = True
        total_files = 0
        total_success = 0
        total_failed = 0
        total_skipped = 0
        total_duration = 0.0

        for phase_name, progress in phases.items():
            duration = progress.duration or 0.0
            percentage = (
                (progress.files_processed / progress.files_total * 100)
                if progress.files_total > 0
                else 0
            )

            table.add_row(
                phase_name.upper(),
                str(progress.files_total),
                str(
                    progress.files_processed
                    - progress.files_failed
                    - progress.files_skipped
                ),
                str(progress.files_failed),
                str(progress.files_skipped),
                f"{percentage:.1f}%",
                f"{duration:.1f}s",
            )

            total_files += progress.files_total
            total_success += (
                progress.files_processed
                - progress.files_failed
                - progress.files_skipped
            )
            total_failed += progress.files_failed
            total_skipped += progress.files_skipped
            total_duration += duration

            if progress.files_failed > 0:
                all_successful = False

        # Add totals row
        total_progress = (
            ((total_success + total_failed + total_skipped) / total_files * 100)
            if total_files > 0
            else 0
        )
        table.add_row(
            "TOTAL",
            str(total_files),
            str(total_success),
            str(total_failed),
            str(total_skipped),
            f"{total_progress:.1f}%",
            f"{total_duration:.1f}s",
            style="bold",
        )

        # Only show summary if there are failures or if debug logging is enabled
        if total_failed > 0:
            logger.warning("\n" + str(table))
            logger.error("\nFailed Files:")
            for file_path, file_progress in files.items():
                if file_progress.status == ProgressStatus.FAILED:
                    logger.error(f"  • {file_path}")
                    if file_progress.error:
                        logger.error(f"    Error: {file_progress.error}")
        else:
            logger.debug("\n" + str(table))

        # Add small delay to prevent overwhelming the event loop
        await asyncio.sleep(0)
