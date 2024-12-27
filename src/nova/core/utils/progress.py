"""
Progress tracking utilities.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, Any, Optional
from datetime import datetime

class ProcessingStatus(Enum):
    """Processing status enum."""
    
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"

@dataclass
class ProcessingProgress:
    """Processing progress data."""
    
    task_id: str
    description: str
    total_files: int = 0
    processed_files: int = 0
    successful_files: int = 0
    failed_files: int = 0
    skipped_files: int = 0
    cached_files: int = 0
    total_bytes: int = 0
    processed_bytes: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: ProcessingStatus = ProcessingStatus.NOT_STARTED
    error_counts: Dict[str, int] = field(default_factory=dict)
    custom_metrics: Dict[str, Any] = field(default_factory=dict)
    current_file: Optional[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if not self.start_time:
            self.start_time = datetime.now()

class ProgressTracker:
    """Track processing progress."""
    
    def __init__(self):
        """Initialize progress tracker."""
        self._tasks: Dict[str, ProcessingProgress] = {}
        
    def start_task(self, task_id: str, description: str, total_files: int = 0) -> ProcessingProgress:
        """Start tracking a new task.
        
        Args:
            task_id: Task identifier
            description: Task description
            total_files: Expected total number of files
            
        Returns:
            New task progress instance
        """
        task = ProcessingProgress(
            task_id=task_id,
            description=description,
            total_files=total_files,
            start_time=datetime.now(),
            status=ProcessingStatus.IN_PROGRESS
        )
        self._tasks[task_id] = task
        return task
        
    def update_task(
        self,
        task_id: str,
        processed_files: int = 0,
        bytes_processed: int = 0,
        successful: bool = True,
        error_type: Optional[str] = None,
        custom_metrics: Optional[Dict[str, Any]] = None,
        cached_files: int = 0,
        current_file: Optional[str] = None
    ) -> ProcessingProgress:
        """Update task progress.
        
        Args:
            task_id: Task identifier
            processed_files: Number of files processed
            bytes_processed: Number of bytes processed
            successful: Whether processing was successful
            error_type: Type of error if unsuccessful
            custom_metrics: Optional custom metrics to track
            cached_files: Number of files loaded from cache
            current_file: Current file being processed
            
        Returns:
            Updated task progress instance
        """
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found")
            
        task.processed_files += processed_files
        task.processed_bytes += bytes_processed
        task.cached_files += cached_files
        
        if successful:
            task.successful_files += processed_files
        else:
            task.failed_files += processed_files
            if error_type:
                task.error_counts[error_type] = task.error_counts.get(error_type, 0) + 1
                
        if custom_metrics:
            task.custom_metrics.update(custom_metrics)
            
        if current_file:
            task.current_file = current_file
            
        return task
        
    def skip_files(self, task_id: str, count: int = 1) -> ProcessingProgress:
        """Mark files as skipped.
        
        Args:
            task_id: Task identifier
            count: Number of files to skip
            
        Returns:
            Updated task progress instance
        """
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found")
            
        task.skipped_files += count
        return task
        
    def complete_task(self, task_id: str, success: bool = True) -> ProcessingProgress:
        """Mark task as complete.
        
        Args:
            task_id: Task identifier
            success: Whether task completed successfully
            
        Returns:
            Updated task progress instance
        """
        task = self._tasks.get(task_id)
        if not task:
            raise KeyError(f"Task {task_id} not found")
            
        task.end_time = datetime.now()
        task.status = ProcessingStatus.COMPLETED if success else ProcessingStatus.FAILED
        return task
        
    def get_task(self, task_id: str) -> Optional[ProcessingProgress]:
        """Get task progress.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task progress instance if found, None otherwise
        """
        return self._tasks.get(task_id)
        
    def get_all_tasks(self) -> Dict[str, ProcessingProgress]:
        """Get all tasks.
        
        Returns:
            Dictionary mapping task IDs to progress instances
        """
        return self._tasks.copy()
        
    def clear_tasks(self) -> None:
        """Clear all tasks."""
        self._tasks.clear() 