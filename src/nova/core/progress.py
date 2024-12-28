"""Progress tracking for Nova pipeline."""
import asyncio
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Dict, Optional


class ProcessingStatus(Enum):
    """Status of file or phase processing."""
    
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class PhaseProgress:
    """Progress tracking for a single phase."""
    
    name: str
    total_files: int
    completed_files: int = 0
    failed_files: int = 0
    status: ProcessingStatus = ProcessingStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get phase duration in seconds."""
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time


@dataclass
class FileProgress:
    """Progress tracking for a single file."""
    
    file_path: Path
    status: ProcessingStatus = ProcessingStatus.PENDING
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    current_phase: Optional[str] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get file processing duration in seconds."""
        if self.start_time is None:
            return None
        end = self.end_time or time.time()
        return end - self.start_time


class ProgressTracker:
    """Track progress of file processing pipeline."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self.phases: Dict[str, PhaseProgress] = {}
        self.files: Dict[Path, FileProgress] = {}
        self._lock = asyncio.Lock()
    
    async def add_phase(self, name: str, total_files: int) -> None:
        """Add a new phase to track.
        
        Args:
            name: Phase name.
            total_files: Total number of files to process.
        """
        async with self._lock:
            self.phases[name] = PhaseProgress(name=name, total_files=total_files)
    
    async def start_file(self, file_path: Path) -> None:
        """Start tracking a file.
        
        Args:
            file_path: Path to file.
        """
        async with self._lock:
            progress = FileProgress(file_path=file_path)
            progress.status = ProcessingStatus.IN_PROGRESS
            progress.start_time = time.time()
            self.files[file_path] = progress
    
    async def complete_file(self, file_path: Path) -> float:
        """Complete file processing.
        
        Args:
            file_path: Path to file.
            
        Returns:
            Processing duration in seconds.
        """
        async with self._lock:
            progress = self.files[file_path]
            progress.status = ProcessingStatus.COMPLETED
            progress.end_time = time.time()
            progress.current_phase = None
            return progress.duration
    
    async def start_phase(self, phase: str, file_path: Path) -> None:
        """Start phase for a file.
        
        Args:
            phase: Phase name.
            file_path: Path to file.
        """
        async with self._lock:
            # Update file progress
            file_progress = self.files[file_path]
            file_progress.current_phase = phase
            
            # Update phase progress
            phase_progress = self.phases[phase]
            if phase_progress.status == ProcessingStatus.PENDING:
                phase_progress.status = ProcessingStatus.IN_PROGRESS
                phase_progress.start_time = time.time()
    
    async def complete_phase(self, phase: str, file_path: Path) -> None:
        """Complete phase for a file.
        
        Args:
            phase: Phase name.
            file_path: Path to file.
        """
        async with self._lock:
            # Update phase progress
            phase_progress = self.phases[phase]
            phase_progress.completed_files += 1
            
            if phase_progress.completed_files == phase_progress.total_files:
                phase_progress.status = ProcessingStatus.COMPLETED
                phase_progress.end_time = time.time()
    
    async def fail_phase(self, phase: str, file_path: Path) -> None:
        """Mark phase as failed for a file.
        
        Args:
            phase: Phase name.
            file_path: Path to file.
        """
        async with self._lock:
            # Update file progress
            file_progress = self.files[file_path]
            file_progress.status = ProcessingStatus.FAILED
            file_progress.end_time = time.time()
            
            # Update phase progress
            phase_progress = self.phases[phase]
            phase_progress.failed_files += 1 