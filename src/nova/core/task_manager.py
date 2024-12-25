"""Manages task tracking and context preservation for multi-step operations."""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, asdict
from enum import Enum
import aiofiles

from .logging import get_logger, print_title, print_stats
from .errors import FileError, with_retry, handle_errors

logger = get_logger(__name__)

class TaskStatus(Enum):
    """Task status enumeration."""
    TODO = "TODO"
    IN_PROGRESS = "IN_PROGRESS"
    DONE = "DONE"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"

@dataclass
class TaskContext:
    """Context data for a task."""
    input_files: List[Path]
    output_files: List[Path]
    metadata: Dict[str, Any]
    dependencies: List[str]
    artifacts: Dict[str, Path]

@dataclass
class Task:
    """Represents a processing task."""
    id: str  # Hierarchical ID (e.g., "1.2.3")
    description: str
    status: TaskStatus
    success_criteria: List[str]
    context: Optional[TaskContext] = None
    parent_id: Optional[str] = None
    subtasks: List['Task'] = None
    
    def __post_init__(self):
        """Initialize subtasks list if None."""
        if self.subtasks is None:
            self.subtasks = []
    
    @property
    def is_leaf(self) -> bool:
        """Check if task is a leaf node (no subtasks)."""
        return not self.subtasks
    
    @property
    def progress(self) -> float:
        """Calculate task progress (0-1)."""
        if self.is_leaf:
            return 1.0 if self.status == TaskStatus.DONE else 0.0
        
        if not self.subtasks:
            return 0.0
        
        completed = sum(task.progress for task in self.subtasks)
        return completed / len(self.subtasks)

class TaskManager:
    """Manages task tracking and context preservation."""
    
    def __init__(self, state_file: Path):
        """Initialize task manager.
        
        Args:
            state_file: Path to state file
        """
        self.state_file = state_file
        self.tasks: Dict[str, Task] = {}
        self.current_task_id: Optional[str] = None
    
    @with_retry()
    @handle_errors()
    async def load_state(self) -> None:
        """Load task state from file."""
        if not self.state_file.exists():
            return
        
        async with aiofiles.open(self.state_file, 'r') as f:
            data = json.loads(await f.read())
            
        # Reconstruct tasks
        for task_data in data['tasks']:
            task = Task(**task_data)
            self.tasks[task.id] = task
        
        self.current_task_id = data.get('current_task_id')
    
    @with_retry()
    @handle_errors()
    async def save_state(self) -> None:
        """Save task state to file."""
        data = {
            'tasks': [asdict(task) for task in self.tasks.values()],
            'current_task_id': self.current_task_id
        }
        
        async with aiofiles.open(self.state_file, 'w') as f:
            await f.write(json.dumps(data, indent=2))
    
    def add_task(
        self,
        description: str,
        success_criteria: List[str],
        parent_id: Optional[str] = None
    ) -> Task:
        """Add a new task.
        
        Args:
            description: Task description
            success_criteria: List of success criteria
            parent_id: Optional parent task ID
            
        Returns:
            Created task
        """
        # Generate task ID
        if parent_id:
            parent = self.tasks[parent_id]
            task_id = f"{parent_id}.{len(parent.subtasks) + 1}"
        else:
            task_id = str(len([t for t in self.tasks.values() if not t.parent_id]) + 1)
        
        # Create task
        task = Task(
            id=task_id,
            description=description,
            status=TaskStatus.TODO,
            success_criteria=success_criteria,
            parent_id=parent_id
        )
        
        # Add to tasks dict
        self.tasks[task_id] = task
        
        # Add to parent's subtasks if applicable
        if parent_id:
            self.tasks[parent_id].subtasks.append(task)
        
        return task
    
    def start_task(self, task_id: str) -> None:
        """Start a task.
        
        Args:
            task_id: ID of task to start
        """
        task = self.tasks[task_id]
        task.status = TaskStatus.IN_PROGRESS
        self.current_task_id = task_id
        
        # Print task info
        print_title(f"Starting Task {task_id}: {task.description}")
        print_stats({
            "Progress": f"{task.progress:.1%}",
            "Status": task.status.value,
            "Subtasks": len(task.subtasks)
        })
    
    def complete_task(
        self,
        task_id: str,
        context: Optional[TaskContext] = None
    ) -> None:
        """Complete a task.
        
        Args:
            task_id: ID of task to complete
            context: Optional context data to preserve
        """
        task = self.tasks[task_id]
        task.status = TaskStatus.DONE
        task.context = context
        
        if task_id == self.current_task_id:
            self.current_task_id = None
        
        # Print completion info
        print_title(f"Completed Task {task_id}: {task.description}")
        print_stats({
            "Progress": "100%",
            "Status": task.status.value,
            "Artifacts": len(context.artifacts) if context else 0
        })
    
    def fail_task(
        self,
        task_id: str,
        error: Optional[str] = None
    ) -> None:
        """Mark a task as failed.
        
        Args:
            task_id: ID of task that failed
            error: Optional error message
        """
        task = self.tasks[task_id]
        task.status = TaskStatus.FAILED
        
        if task_id == self.current_task_id:
            self.current_task_id = None
        
        # Print failure info
        print_title(f"Failed Task {task_id}: {task.description}")
        print_stats({
            "Status": task.status.value,
            "Error": error or "Unknown error"
        })
    
    def get_progress(self) -> Dict[str, Any]:
        """Get overall progress statistics.
        
        Returns:
            Dictionary of progress statistics
        """
        total_tasks = len(self.tasks)
        completed = len([t for t in self.tasks.values() if t.status == TaskStatus.DONE])
        failed = len([t for t in self.tasks.values() if t.status == TaskStatus.FAILED])
        
        return {
            "total_tasks": total_tasks,
            "completed_tasks": completed,
            "failed_tasks": failed,
            "progress": completed / total_tasks if total_tasks > 0 else 0.0,
            "current_task": self.current_task_id
        }

__all__ = ['TaskManager', 'Task', 'TaskContext', 'TaskStatus'] 