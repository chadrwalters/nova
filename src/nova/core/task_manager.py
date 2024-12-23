"""Task manager for handling processing tasks."""

from typing import Any, Dict, List, Optional
from pathlib import Path
import asyncio
from datetime import datetime

class TaskManager:
    """Manages processing tasks and their execution."""
    
    def __init__(self):
        """Initialize task manager."""
        self.tasks: Dict[str, Dict[str, Any]] = {}
        self.task_queue = asyncio.Queue()
        self.running = False
        
    def add_task(self, task_id: str, task_type: str, source_path: Path, dest_path: Path, metadata: Optional[Dict[str, Any]] = None) -> None:
        """Add a task to the queue.
        
        Args:
            task_id: Unique task identifier
            task_type: Type of task (e.g., 'copy', 'process', 'convert')
            source_path: Source file path
            dest_path: Destination file path
            metadata: Optional metadata for the task
        """
        task = {
            'id': task_id,
            'type': task_type,
            'source': source_path,
            'destination': dest_path,
            'metadata': metadata or {},
            'status': 'pending',
            'created': datetime.now().isoformat(),
            'started': None,
            'completed': None,
            'error': None
        }
        
        self.tasks[task_id] = task
        self.task_queue.put_nowait(task)
        
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get task details.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Task details or None if not found
        """
        return self.tasks.get(task_id)
        
    def update_task(self, task_id: str, status: str, error: Optional[str] = None) -> None:
        """Update task status.
        
        Args:
            task_id: Task identifier
            status: New status
            error: Optional error message
        """
        if task_id in self.tasks:
            self.tasks[task_id].update({
                'status': status,
                'error': error,
                'completed': datetime.now().isoformat() if status in ('completed', 'failed') else None
            })
            
    def get_pending_tasks(self) -> List[Dict[str, Any]]:
        """Get list of pending tasks.
        
        Returns:
            List of pending tasks
        """
        return [task for task in self.tasks.values() if task['status'] == 'pending']
        
    def get_failed_tasks(self) -> List[Dict[str, Any]]:
        """Get list of failed tasks.
        
        Returns:
            List of failed tasks
        """
        return [task for task in self.tasks.values() if task['status'] == 'failed']
        
    def clear_completed_tasks(self) -> None:
        """Clear completed tasks from the task list."""
        self.tasks = {
            task_id: task 
            for task_id, task in self.tasks.items() 
            if task['status'] not in ('completed', 'failed')
        } 