"""
Progress tracking utilities.
"""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional, Dict, Any

logger = logging.getLogger(__name__)

class ProcessingStatus(Enum):
    """Status of a processing task."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

@dataclass
class ProcessingProgress:
    """Progress information for a processing task."""
    status: ProcessingStatus
    start_time: datetime
    end_time: Optional[datetime] = None
    current_step: Optional[str] = None
    total_steps: Optional[int] = None
    current_step_number: Optional[int] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    @property
    def duration(self) -> Optional[float]:
        """Get the duration of the task in seconds."""
        if self.end_time and self.start_time:
            return (self.end_time - self.start_time).total_seconds()
        return None
    
    @property
    def progress_percentage(self) -> Optional[float]:
        """Get the progress percentage."""
        if self.total_steps and self.current_step_number:
            return (self.current_step_number / self.total_steps) * 100
        return None
    
    def update(
        self,
        status: Optional[ProcessingStatus] = None,
        step: Optional[str] = None,
        step_number: Optional[int] = None,
        error: Optional[str] = None,
        **metadata
    ) -> None:
        """Update the progress information."""
        if status:
            self.status = status
            if status == ProcessingStatus.COMPLETED:
                self.end_time = datetime.now()
            elif status == ProcessingStatus.FAILED:
                self.end_time = datetime.now()
        
        if step:
            self.current_step = step
        
        if step_number is not None:
            self.current_step_number = step_number
        
        if error:
            self.error = error
        
        self.metadata.update(metadata)
        
        # Log the update
        message = f"Processing {self.status.value}"
        if self.current_step:
            message += f": {self.current_step}"
        if self.progress_percentage is not None:
            message += f" ({self.progress_percentage:.1f}%)"
        if error:
            message += f" - Error: {error}"
        
        log_level = logging.ERROR if status == ProcessingStatus.FAILED else logging.INFO
        logger.log(log_level, message)

class ProgressTracker:
    """Track progress of multiple processing tasks."""
    
    def __init__(self):
        self.tasks: Dict[str, ProcessingProgress] = {}
    
    def start_task(
        self,
        task_id: str,
        total_steps: Optional[int] = None,
        **metadata
    ) -> ProcessingProgress:
        """Start tracking a new task."""
        progress = ProcessingProgress(
            status=ProcessingStatus.IN_PROGRESS,
            start_time=datetime.now(),
            total_steps=total_steps,
            current_step_number=0,
            metadata=metadata
        )
        self.tasks[task_id] = progress
        return progress
    
    def update_task(
        self,
        task_id: str,
        status: Optional[ProcessingStatus] = None,
        step: Optional[str] = None,
        step_number: Optional[int] = None,
        error: Optional[str] = None,
        **metadata
    ) -> None:
        """Update a task's progress."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not found")
        
        self.tasks[task_id].update(
            status=status,
            step=step,
            step_number=step_number,
            error=error,
            **metadata
        )
    
    def complete_task(
        self,
        task_id: str,
        error: Optional[str] = None,
        **metadata
    ) -> None:
        """Mark a task as completed or failed."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not found")
        
        status = ProcessingStatus.FAILED if error else ProcessingStatus.COMPLETED
        self.tasks[task_id].update(status=status, error=error, **metadata)
    
    def get_task(self, task_id: str) -> ProcessingProgress:
        """Get a task's progress."""
        if task_id not in self.tasks:
            raise KeyError(f"Task {task_id} not found")
        return self.tasks[task_id]
    
    def get_all_tasks(self) -> Dict[str, ProcessingProgress]:
        """Get all tasks' progress."""
        return self.tasks.copy() 