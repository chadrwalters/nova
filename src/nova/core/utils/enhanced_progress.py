"""Enhanced progress tracking with custom columns and detailed metrics."""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path
import time

from rich.progress import (
    Progress, SpinnerColumn, TimeElapsedColumn, 
    BarColumn, TaskProgressColumn, TimeRemainingColumn,
    FileSizeColumn, TransferSpeedColumn, TextColumn
)
from rich.table import Table
from rich.text import Text

from nova.core.utils.metrics import MetricsTracker
from nova.core.console.logger import ConsoleLogger


class ProgressColumnType(Enum):
    """Types of progress columns available."""
    SPINNER = "spinner"
    TIME_ELAPSED = "time_elapsed"
    BAR = "bar"
    PROGRESS = "progress"
    TIME_REMAINING = "time_remaining"
    FILE_SIZE = "file_size"
    SPEED = "speed"
    TEXT = "text"
    CUSTOM = "custom"


@dataclass
class ProgressColumn:
    """Configuration for a progress column."""
    type: ProgressColumnType
    header: str
    width: Optional[int] = None
    style: str = "none"
    justify: str = "left"
    format_str: str = "{}"


@dataclass
class ProgressConfig:
    """Configuration for progress tracking."""
    columns: List[ProgressColumn] = field(default_factory=list)
    show_eta: bool = True
    show_speed: bool = True
    show_size: bool = True
    refresh_per_second: int = 10
    transient: bool = False
    expand: bool = True


@dataclass
class FileProgress:
    """Progress information for a single file."""
    path: Path
    size: int
    processed_bytes: int = 0
    status: str = "pending"
    error: Optional[str] = None
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    @property
    def duration(self) -> Optional[float]:
        """Get processing duration in seconds."""
        if not self.start_time:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()
    
    @property
    def speed(self) -> Optional[float]:
        """Get processing speed in bytes per second."""
        if not self.duration:
            return None
        return self.processed_bytes / self.duration if self.duration > 0 else 0


class EnhancedProgress:
    """Enhanced progress tracking with custom columns and detailed metrics."""

    def __init__(
        self,
        description: str,
        config: Optional[ProgressConfig] = None,
        logger: Optional[ConsoleLogger] = None,
        metrics: Optional[MetricsTracker] = None
    ):
        """Initialize progress tracker.
        
        Args:
            description: Progress description
            config: Progress configuration
            logger: Console logger instance
            metrics: Optional metrics tracker instance
        """
        self.description = description
        self.config = config or ProgressConfig()
        self.logger = logger or ConsoleLogger()
        self.metrics = metrics or MetricsTracker()
        
        # Initialize progress tracking
        self.progress = self._create_progress()
        self.task_id = None
        self.files: Dict[Path, FileProgress] = {}
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None
        
    def _create_progress(self) -> Progress:
        """Create progress bar with configured columns."""
        columns = []
        
        # Add configured columns
        for col in self.config.columns:
            if col.type == ProgressColumnType.SPINNER:
                columns.append(SpinnerColumn())
            elif col.type == ProgressColumnType.TIME_ELAPSED:
                columns.append(TimeElapsedColumn())
            elif col.type == ProgressColumnType.BAR:
                columns.append(BarColumn(complete_style=col.style))
            elif col.type == ProgressColumnType.PROGRESS:
                columns.append(TaskProgressColumn())
            elif col.type == ProgressColumnType.TIME_REMAINING:
                columns.append(TimeRemainingColumn())
            elif col.type == ProgressColumnType.FILE_SIZE:
                columns.append(FileSizeColumn())
            elif col.type == ProgressColumnType.SPEED:
                columns.append(TransferSpeedColumn())
            elif col.type == ProgressColumnType.TEXT:
                columns.append(TextColumn(
                    col.format_str,
                    style=col.style,
                    justify=col.justify,
                    width=col.width
                ))
                
        # Add default columns if none configured
        if not columns:
            columns = [
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn()
            ]
            
            if self.config.show_size:
                columns.append(FileSizeColumn())
            if self.config.show_speed:
                columns.append(TransferSpeedColumn())
            if self.config.show_eta:
                columns.append(TimeRemainingColumn())
                
        return Progress(
            *columns,
            refresh_per_second=self.config.refresh_per_second,
            transient=self.config.transient,
            expand=self.config.expand
        )
        
    def start(self, total_files: int, total_size: Optional[int] = None) -> None:
        """Start progress tracking.
        
        Args:
            total_files: Total number of files to process
            total_size: Total size in bytes (optional)
        """
        self.start_time = datetime.now()
        self.metrics.start_timer("processing")
        
        description = f"{self.description} ({total_files} files"
        if total_size:
            description += f", {total_size / 1024 / 1024:.1f} MB"
        description += ")"
        
        self.progress.start()
        self.task_id = self.progress.add_task(
            description,
            total=total_files
        )
        
        # Initialize metrics
        self.metrics.set_gauge("total_files", total_files)
        if total_size:
            self.metrics.set_gauge("total_bytes", total_size)

    def add_file(self, path: Path, size: int) -> None:
        """Add a file to track.
        
        Args:
            path: File path
            size: File size in bytes
        """
        self.files[path] = FileProgress(path=path, size=size)
        self.metrics.increment("files_added")
        self.metrics.set_gauge("total_bytes", size, labels={"file": str(path)})
        
    def update_file(
        self,
        path: Path,
        processed_bytes: Optional[int] = None,
        status: Optional[str] = None,
        error: Optional[str] = None
    ) -> None:
        """Update file progress.
        
        Args:
            path: File path
            processed_bytes: Number of bytes processed
            status: Processing status
            error: Error message if failed
        """
        file_progress = self.files.get(path)
        if not file_progress:
            return
            
        # Update progress
        if processed_bytes is not None:
            file_progress.processed_bytes = processed_bytes
            self.metrics.set_gauge("processed_bytes", processed_bytes, labels={"file": str(path)})
            
        # Update status
        if status:
            file_progress.status = status
            if status == "completed":
                file_progress.end_time = datetime.now()
                self.metrics.increment("files_completed")
                if file_progress.duration:
                    self.metrics.add_timing("file_duration", file_progress.duration, labels={"file": str(path)})
            elif status == "failed":
                file_progress.end_time = datetime.now()
                self.metrics.increment("files_failed")
                
        # Update error
        if error:
            file_progress.error = error
            self.metrics.increment("file_errors", labels={"file": str(path), "error": error})
            
        # Update overall progress
        if self.task_id is not None:
            completed = len([f for f in self.files.values() if f.status in ["completed", "failed"]])
            self.progress.update(self.task_id, completed=completed)
            
    def get_stats(self) -> Dict[str, Any]:
        """Get current progress statistics.
        
        Returns:
            Dictionary of progress statistics
        """
        stats = {
            "total_files": len(self.files),
            "completed_files": len([f for f in self.files.values() if f.status == "completed"]),
            "failed_files": len([f for f in self.files.values() if f.status == "failed"]),
            "pending_files": len([f for f in self.files.values() if f.status == "pending"]),
            "total_bytes": sum(f.size for f in self.files.values()),
            "processed_bytes": sum(f.processed_bytes for f in self.files.values()),
            "errors": [f.error for f in self.files.values() if f.error]
        }
        
        if self.start_time:
            duration = (datetime.now() - self.start_time).total_seconds()
            stats["duration"] = duration
            if stats["processed_bytes"] > 0 and duration > 0:
                stats["speed"] = stats["processed_bytes"] / duration
                
        return stats
        
    def stop(self) -> None:
        """Stop progress tracking."""
        self.end_time = datetime.now()
        self.progress.stop()
        
        # Update final metrics
        if self.start_time:
            duration = (self.end_time - self.start_time).total_seconds()
            self.metrics.add_timing("total_duration", duration)
            
            stats = self.get_stats()
            if stats["processed_bytes"] > 0 and duration > 0:
                self.metrics.set_gauge("processing_speed", stats["speed"]) 