"""Progress tracking for Nova pipeline."""
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set

from rich.progress import Progress


class ProgressStatus(Enum):
    """Status of a progress item."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class PhaseProgress:
    """Progress tracking for a pipeline phase."""

    name: str
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[float] = None
    duration: Optional[float] = None
    files_total: int = 0
    files_processed: int = 0
    files_failed: int = 0
    files_skipped: int = 0
    files_unchanged: Set[Path] = field(default_factory=set)
    files_reprocessed: Set[Path] = field(default_factory=set)
    failures: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class FileProgress:
    """Progress tracking for a file."""

    file_path: Path
    status: ProgressStatus = ProgressStatus.PENDING
    start_time: Optional[float] = None
    duration: Optional[float] = None
    error: Optional[str] = None


class ProgressTracker:
    """Track progress of pipeline execution."""

    def __init__(self) -> None:
        """Initialize progress tracker."""
        self.phases: Dict[str, PhaseProgress] = {}
        self.files: Dict[Path, FileProgress] = {}
        self.current_phase: Optional[str] = None
        self.current_file: Optional[Path] = None
        self._progress: Optional[Progress] = None
        self._task_id: Optional[int] = None

    def set_progress_bar(self, progress: Progress, task_id: int) -> None:
        """Set progress bar for tracking.

        Args:
            progress: Progress bar instance
            task_id: Task ID for updating progress
        """
        self._progress = progress
        self._task_id = task_id

    def _update_progress(self) -> None:
        """Update progress bar if available."""
        if self._progress is not None and self._task_id is not None:
            phase = self.phases.get(self.current_phase) if self.current_phase else None
            if phase and phase.files_total > 0:
                progress = (phase.files_processed / phase.files_total) * 100
                self._progress.update(self._task_id, completed=progress)

    def add_phase(self, phase_name: str) -> None:
        """Add a phase to track.

        Args:
            phase_name: Name of the phase
        """
        if phase_name not in self.phases:
            self.phases[phase_name] = PhaseProgress(name=phase_name)

    def add_file(self, file_path: Path) -> None:
        """Add a file to track.

        Args:
            file_path: Path to the file
        """
        if file_path not in self.files:
            self.files[file_path] = FileProgress(file_path=file_path)

    def set_files_total(self, phase_name: str, total: int) -> None:
        """Set total number of files for a phase.

        Args:
            phase_name: Name of the phase
            total: Total number of files
        """
        if phase_name in self.phases:
            self.phases[phase_name].files_total = total

    def mark_file_unchanged(self, phase_name: str, file_path: Path) -> None:
        """Mark a file as unchanged.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
        """
        if phase_name in self.phases:
            self.phases[phase_name].files_unchanged.add(file_path)

    def mark_file_reprocessed(self, phase_name: str, file_path: Path) -> None:
        """Mark a file as reprocessed.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
        """
        if phase_name in self.phases:
            self.phases[phase_name].files_reprocessed.add(file_path)

    def add_failure(self, phase_name: str, file_path: Path, error: str) -> None:
        """Add a failure record.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
            error: Error message
        """
        if phase_name in self.phases:
            self.phases[phase_name].failures.append(
                {"file": str(file_path), "error": error, "phase": phase_name}
            )

    async def start_phase(self, phase_name: str) -> None:
        """Start tracking a phase.

        Args:
            phase_name: Name of the phase
        """
        if phase_name in self.phases:
            phase = self.phases[phase_name]
            phase.status = ProgressStatus.RUNNING
            phase.start_time = time.time()
            self.current_phase = phase_name

    async def end_phase(self, phase_name: str) -> None:
        """End tracking a phase.

        Args:
            phase_name: Name of the phase
        """
        if phase_name in self.phases:
            phase = self.phases[phase_name]
            if phase.start_time is not None:
                phase.duration = time.time() - phase.start_time
            phase.status = ProgressStatus.COMPLETED
            if self.current_phase == phase_name:
                self.current_phase = None

    async def start_file(self, phase_name: str, file_path: Path) -> None:
        """Start tracking a file.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
        """
        if phase_name in self.phases and file_path in self.files:
            file = self.files[file_path]
            file.status = ProgressStatus.RUNNING
            file.start_time = time.time()
            self.current_file = file_path

    async def end_file(
        self,
        phase_name: str,
        file_path: Path,
        status: ProgressStatus = ProgressStatus.COMPLETED,
        error: Optional[str] = None,
    ) -> None:
        """End tracking a file.

        Args:
            phase_name: Name of the phase
            file_path: Path to the file
            status: Final status of the file
            error: Error message if failed
        """
        if phase_name in self.phases and file_path in self.files:
            phase = self.phases[phase_name]
            file = self.files[file_path]

            # Update file status
            file.status = status
            if file.start_time is not None:
                file.duration = time.time() - file.start_time
            if error:
                file.error = error

            # Update phase counters
            phase.files_processed += 1
            if status == ProgressStatus.FAILED:
                phase.files_failed += 1
            elif status == ProgressStatus.SKIPPED:
                # Don't count .DS_Store files in skipped count
                if not str(file_path).endswith(".DS_Store"):
                    phase.files_skipped += 1

            # Update progress bar
            self._update_progress()

            if self.current_file == file_path:
                self.current_file = None

            # Add small delay to prevent overwhelming the event loop
            await asyncio.sleep(0)
