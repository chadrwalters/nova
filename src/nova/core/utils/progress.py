"""
Progress tracking utilities.
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, Optional

class ProcessingStatus(Enum):
    NOT_STARTED = "NOT_STARTED"
    IN_PROGRESS = "IN_PROGRESS"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

@dataclass
class ProcessingProgress:
    """Class to track progress of a processing task"""
    task_id: str
    description: str
    total_files: int = 0
    processed_files: int = 0
    cached_files: int = 0
    skipped_files: int = 0
    failed_files: int = 0
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    status: ProcessingStatus = ProcessingStatus.NOT_STARTED
    current_file: Optional[str] = None
    error_message: Optional[str] = None

    @property
    def elapsed_time(self) -> Optional[float]:
        """Get elapsed time in seconds."""
        if not self.start_time:
            return None
        end = self.end_time or datetime.now()
        return (end - self.start_time).total_seconds()

    @property
    def status_value(self) -> Optional[str]:
        """Get status value safely."""
        return self.status.value if self.status else None

class ProgressTracker:
    """Track progress of multiple processing tasks."""
    def __init__(self):
        self._tasks: Dict[str, ProcessingProgress] = {}

    def start_task(self, task_id: str, description: str, total_files: int = 0) -> ProcessingProgress:
        """Start tracking a new task."""
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
        processed_files: Optional[int] = None,
        cached_files: Optional[int] = None,
        skipped_files: Optional[int] = None,
        failed_files: Optional[int] = None,
        current_file: Optional[str] = None,
        error_message: Optional[str] = None,
        status: Optional[ProcessingStatus] = None
    ) -> ProcessingProgress:
        """Update task progress."""
        task = self._tasks.get(task_id)
        if not task:
            # Create task if it doesn't exist
            task = ProcessingProgress(
                task_id=task_id,
                description=f"Task {task_id}",
                total_files=0,
                start_time=datetime.now(),
                status=ProcessingStatus.IN_PROGRESS
            )
            self._tasks[task_id] = task

        if processed_files is not None:
            task.processed_files = processed_files
        if cached_files is not None:
            task.cached_files = cached_files
        if skipped_files is not None:
            task.skipped_files = skipped_files
        if failed_files is not None:
            task.failed_files = failed_files
        if current_file is not None:
            task.current_file = current_file
        if error_message is not None:
            task.error_message = error_message
        if status is not None:
            task.status = status

        return task

    def complete_task(self, task_id: str, status: ProcessingStatus = ProcessingStatus.COMPLETED) -> ProcessingProgress:
        """Mark a task as complete."""
        task = self._tasks.get(task_id)
        if not task:
            # Create task if it doesn't exist
            task = ProcessingProgress(
                task_id=task_id,
                description=f"Task {task_id}",
                total_files=0,
                start_time=datetime.now(),
                status=status,
                end_time=datetime.now()
            )
            self._tasks[task_id] = task
        else:
            task.status = status
            task.end_time = datetime.now()
        return task

    def get_task(self, task_id: str) -> Optional[ProcessingProgress]:
        """Get task progress."""
        return self._tasks.get(task_id)

    def get_all_tasks(self) -> Dict[str, ProcessingProgress]:
        """Get all tasks."""
        return self._tasks.copy()

    def clear_tasks(self) -> None:
        """Clear all tasks."""
        self._tasks.clear() 