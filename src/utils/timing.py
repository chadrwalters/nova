from functools import wraps
from datetime import datetime
from typing import Callable, Any
from contextlib import contextmanager
from src.utils.colors import NovaConsole

nova_console = NovaConsole()

class Timer:
    def __init__(self):
        self.start_time = datetime.now()
        self.last_checkpoint = self.start_time
        
    def checkpoint(self, name: str) -> float:
        """Record a checkpoint and return duration since last checkpoint."""
        now = datetime.now()
        duration = (now - self.last_checkpoint).total_seconds()
        self.last_checkpoint = now
        return duration
        
    def total(self) -> float:
        """Get total duration since timer started."""
        return (datetime.now() - self.start_time).total_seconds()

@contextmanager
def timed_section(name: str):
    """
    Context manager for timing a section of code.
    
    Args:
        name: Name of the section being timed
    """
    start_time = datetime.now()
    nova_console.process_start(name)
    try:
        yield
    finally:
        duration = (datetime.now() - start_time).total_seconds()
        nova_console.process_end(f"{name} completed in {duration:.2f}s")