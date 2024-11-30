from functools import wraps
from datetime import datetime
from typing import Callable, Any
from colors import NovaConsole

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
        """Get total duration in seconds."""
        return (datetime.now() - self.start_time).total_seconds()

def format_duration(seconds: float) -> str:
    """Format duration in a human-readable way."""
    if seconds < 60:
        return f"{seconds:.2f}s"
    minutes = int(seconds / 60)
    seconds = seconds % 60
    return f"{minutes}m {seconds:.2f}s"

def timed_section(section_name: str) -> Callable:
    """Decorator to time and log section execution."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            nova_console.section(section_name)
            
            start_time = datetime.now()
            result = func(*args, **kwargs)
            duration = (datetime.now() - start_time).total_seconds()
            
            nova_console.console.print(f"[bright_green]✓[/] {section_name} completed in [bright_cyan]{format_duration(duration)}[/]")
            nova_console.console.print()
            return result
        return wrapper
    return decorator 