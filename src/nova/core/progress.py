"""Progress tracking for Nova pipeline."""
import asyncio
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.table import Table
from rich.panel import Panel

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
    task_id: Optional[int] = None
    
    @property
    def remaining_files(self) -> int:
        """Get number of remaining files."""
        return self.total_files - (self.completed_files + self.failed_files + self.skipped_files)
    
    @property
    def progress_percentage(self) -> float:
        """Get progress percentage."""
        if self.total_files == 0:
            return 100.0
        return (self.completed_files + self.failed_files + self.skipped_files) / self.total_files * 100


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
        
        # Initialize rich progress display
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            console=self.console
        )
        self.progress.start()
        
    async def add_phase(self, phase_name: str, total_files: int) -> None:
        """Add a new phase to track.
        
        Args:
            phase_name: Name of the phase
            total_files: Total number of files to process
        """
        async with self.lock:
            # Create phase progress
            phase = PhaseProgress(
                name=phase_name,
                total_files=total_files
            )
            
            # Add progress bar
            phase.task_id = self.progress.add_task(
                f"[cyan]{phase_name.upper()}",
                total=total_files
            )
            
            self.phases[phase_name] = phase
            
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
            
    async def fail_phase(self, phase_name: str, file_path: Path, error_message: Optional[str] = None) -> None:
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
                self.progress.update(phase.task_id, completed=phase.completed_files + phase.failed_files)
            
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
                self.progress.update(phase.task_id, completed=phase.completed_files + phase.failed_files + phase.skipped_files)
            
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
            
    async def fail_file(self, file_path: Path, error_message: Optional[str] = None) -> None:
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
        # Get phase stats
        phase_stats = []
        all_successful = True
        
        for phase_name, phase_state in self.phases.items():
            total = len(phase_state.files)
            completed = len([f for f in phase_state.files.values() if f.status == FileStatus.COMPLETED])
            failed = len([f for f in phase_state.files.values() if f.status == FileStatus.FAILED])
            skipped = len([f for f in phase_state.files.values() if f.status == FileStatus.SKIPPED])
            
            # Calculate progress percentage
            progress = (completed / total * 100) if total > 0 else 0
            
            phase_stats.append({
                'phase': phase_name.upper(),
                'total': total,
                'completed': completed,
                'failed': failed,
                'skipped': skipped,
                'progress': f"{progress:.1f}%"
            })
            
            # Check for failures
            if failed > 0:
                all_successful = False
        
        # Create summary table
        table = Table(title="Processing Summary")
        table.add_column("Phase", style="cyan")
        table.add_column("Total", justify="right", style="green")
        table.add_column("Completed", justify="right", style="green")
        table.add_column("Failed", justify="right", style="red")
        table.add_column("Skipped", justify="right", style="yellow")
        table.add_column("Progress", justify="right", style="green")
        
        for stats in phase_stats:
            table.add_row(
                stats['phase'],
                str(stats['total']),
                str(stats['completed']),
                str(stats['failed']),
                str(stats['skipped']),
                stats['progress']
            )
        
        # Log summary
        logger = logging.getLogger("nova.summary")
        logger.info("\n" + str(table))
        
        if all_successful:
            logger.info("All files processed successfully!")
        else:
            logger.warning("Some files failed to process. Check the logs for details.") 