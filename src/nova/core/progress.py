"""Progress tracking for Nova pipeline."""
import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
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

logger = logging.getLogger(__name__)


class ProcessingStatus(Enum):
    """Status of file processing."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseProgress:
    """Progress tracking for a phase."""

    name: str
    total_files: int
    completed_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    files_in_progress: Set[Path] = field(default_factory=set)
    completed_file_paths: Set[Path] = field(default_factory=set)
    failed_file_paths: Set[Path] = field(default_factory=set)
    skipped_file_paths: Set[Path] = field(default_factory=set)
    files: Dict[Path, "FileProgress"] = field(default_factory=dict)
    task_id: Optional[int] = None
    duration: Optional[float] = None

    @property
    def remaining_files(self) -> int:
        """Get number of remaining files."""
        return self.total_files - (
            self.completed_files + self.failed_files + self.skipped_files
        )

    @property
    def progress_percentage(self) -> float:
        """Get progress percentage."""
        if self.total_files == 0:
            return 100.0
        return (
            (self.completed_files + self.failed_files + self.skipped_files)
            / self.total_files
            * 100
        )


@dataclass
class FileProgress:
    """Progress tracking for a file."""

    path: Path
    status: ProcessingStatus = ProcessingStatus.PENDING
    current_phase: Optional[str] = None
    completed_phases: Set[str] = field(default_factory=set)
    failed_phases: Set[str] = field(default_factory=set)
    skipped_phases: Set[str] = field(default_factory=set)
    error_message: Optional[str] = None


class ProgressTracker:
    """Track progress of file processing through phases."""

    def __init__(self):
        """Initialize progress tracker."""
        self.console = Console()
        self.phases: Dict[str, PhaseProgress] = {}
        self.files: Dict[Path, FileProgress] = {}
        self.lock = asyncio.Lock()

        # Initialize rich progress display with better formatting
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

    async def add_phase(self, phase_name: str, total_files: int) -> None:
        """Add a new phase to track."""
        async with self.lock:
            phase = PhaseProgress(name=phase_name, total_files=total_files)

            # Add progress bar with better formatting
            phase.task_id = self.progress.add_task(
                phase_name.upper(),
                total=total_files,
                start=True,
                visible=True,  # Ensure phase is visible
            )

            self.phases[phase_name] = phase

    async def update_progress(
        self,
        phase_name: str,
        file_path: Path,
        status: ProcessingStatus,
        error: Optional[str] = None,
    ) -> None:
        """Update progress for a file."""
        async with self.lock:
            phase = self.phases[phase_name]

            # Update counts based on status
            if status == ProcessingStatus.COMPLETED:
                phase.completed_files += 1
                phase.completed_file_paths.add(file_path)
                if file_path in phase.files_in_progress:
                    phase.files_in_progress.remove(file_path)
            elif status == ProcessingStatus.FAILED:
                phase.failed_files += 1
                phase.failed_file_paths.add(file_path)
                if file_path in phase.files_in_progress:
                    phase.files_in_progress.remove(file_path)
                if error:
                    logger.error(f"Failed to process {file_path.name}: {error}")
            elif status == ProcessingStatus.SKIPPED:
                phase.skipped_files += 1
                phase.skipped_file_paths.add(file_path)
            elif status == ProcessingStatus.IN_PROGRESS:
                phase.files_in_progress.add(file_path)

            # Update progress bar
            completed = phase.completed_files + phase.failed_files + phase.skipped_files
            self.progress.update(
                phase.task_id,
                completed=completed,
                description=f"{phase_name.upper():>12}",
                visible=True,  # Ensure phase remains visible
            )

    def start_phase(self, phase_name: str) -> None:
        """Start timing a phase."""
        if phase_name in self.phases:
            phase = self.phases[phase_name]
            phase.start_time = time.time()
            logger.debug(f"[cyan]Starting {phase_name.upper()} phase[/]")

    def end_phase(self, phase_name: str) -> None:
        """End timing a phase and update duration."""
        if phase_name in self.phases:
            phase = self.phases[phase_name]
            if phase.start_time is not None:
                phase.duration = time.time() - phase.start_time
                logger.debug(
                    f"[cyan]Completed {phase_name.upper()} phase[/] in {phase.duration:.1f}s"
                )

    async def start_file(self, file_path: Path) -> None:
        """Start tracking a file.

        Args:
            file_path: Path to the file
        """
        async with self.lock:
            if file_path not in self.files:
                self.files[file_path] = FileProgress(path=file_path)

            file_progress = self.files[file_path]
            file_progress.status = ProcessingStatus.IN_PROGRESS

    async def start_phase(self, phase_name: str, file_path: Path) -> None:
        """Start processing a file in a phase.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
        """
        async with self.lock:
            phase = self.phases[phase_name]
            phase.files_in_progress.add(file_path)

            file_progress = self.files[file_path]
            file_progress.current_phase = phase_name

    async def complete_phase(self, phase_name: str, file_path: Path) -> None:
        """Complete processing a file in a phase.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
        """
        async with self.lock:
            phase = self.phases[phase_name]
            phase.files_in_progress.remove(file_path)
            phase.completed_files += 1
            phase.completed_file_paths.add(file_path)

            # Update progress bar
            if phase.task_id is not None:
                self.progress.update(phase.task_id, completed=phase.completed_files)

            file_progress = self.files[file_path]
            file_progress.completed_phases.add(phase_name)
            file_progress.current_phase = None

    async def fail_phase(
        self, phase_name: str, file_path: Path, error_message: Optional[str] = None
    ) -> None:
        """Mark a file as failed in a phase.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
            error_message: Optional error message
        """
        async with self.lock:
            phase = self.phases[phase_name]
            if file_path in phase.files_in_progress:
                phase.files_in_progress.remove(file_path)
            phase.failed_files += 1
            phase.failed_file_paths.add(file_path)

            # Update progress bar
            if phase.task_id is not None:
                self.progress.update(
                    phase.task_id, completed=phase.completed_files + phase.failed_files
                )

            file_progress = self.files[file_path]
            file_progress.failed_phases.add(phase_name)
            file_progress.current_phase = None
            if error_message:
                file_progress.error_message = error_message

    async def skip_phase(self, phase_name: str, file_path: Path) -> None:
        """Mark a file as skipped in a phase.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
        """
        async with self.lock:
            phase = self.phases[phase_name]
            phase.skipped_files += 1
            phase.skipped_file_paths.add(file_path)

            # Update progress bar
            if phase.task_id is not None:
                self.progress.update(
                    phase.task_id,
                    completed=phase.completed_files
                    + phase.failed_files
                    + phase.skipped_files,
                )

            file_progress = self.files[file_path]
            file_progress.skipped_phases.add(phase_name)

    async def complete_file(self, file_path: Path) -> None:
        """Complete processing a file.

        Args:
            file_path: Path to the file
        """
        async with self.lock:
            file_progress = self.files[file_path]
            file_progress.status = ProcessingStatus.COMPLETED

    async def fail_file(
        self, file_path: Path, error_message: Optional[str] = None
    ) -> None:
        """Mark a file as failed.

        Args:
            file_path: Path to the file
            error_message: Optional error message
        """
        async with self.lock:
            file_progress = self.files[file_path]
            file_progress.status = ProcessingStatus.FAILED
            if error_message:
                file_progress.error_message = error_message

    async def print_summary(self) -> None:
        """Print processing summary."""
        # Stop the progress display before showing summary
        self.progress.stop()

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
        total_completed = 0
        total_failed = 0
        total_skipped = 0
        total_duration = 0.0

        for phase_name, phase_state in self.phases.items():
            completed = phase_state.completed_files
            failed = phase_state.failed_files
            skipped = phase_state.skipped_files
            duration = phase_state.duration or 0.0

            # Calculate progress percentage
            progress = phase_state.progress_percentage

            table.add_row(
                phase_name.upper(),
                str(phase_state.total_files),
                str(completed),
                str(failed),
                str(skipped),
                f"{progress:.1f}%",
                f"{duration:.1f}s",
            )

            total_files += phase_state.total_files
            total_completed += completed
            total_failed += failed
            total_skipped += skipped
            total_duration += duration

            if failed > 0:
                all_successful = False

        # Add totals row
        total_progress = (
            (total_completed + total_failed + total_skipped) / total_files * 100
            if total_files > 0
            else 0
        )
        table.add_row(
            "TOTAL",
            str(total_files),
            str(total_completed),
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
            for phase_state in self.phases.values():
                for file_path in phase_state.failed_file_paths:
                    logger.error(f"  • {file_path}")
        else:
            logger.debug("\n" + str(table))
