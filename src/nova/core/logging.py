"""Nova logging configuration."""
import logging
import time
from typing import Dict, Optional, Any, List
from pathlib import Path
import os
from datetime import datetime

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..config.settings import LoggingConfig

# Initialize console with force terminal
console = Console(force_terminal=True)


class NovaLogRecord(logging.LogRecord):
    """Extended LogRecord with Nova-specific fields."""
    
    def __init__(self, *args, **kwargs):
        """Initialize log record with Nova-specific fields."""
        super().__init__(*args, **kwargs)
        self.phase = None
        self.handler = None
        self.duration = None
        self.context = {}
        self.file_path = None
        self.progress = None


class NovaLogger(logging.Logger):
    """Extended Logger with Nova-specific methods."""
    
    def makeRecord(self, name, level, fn, lno, msg, args, exc_info, func=None, extra=None, sinfo=None):
        """Create a NovaLogRecord instead of LogRecord."""
        record = NovaLogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra:
            for key, value in extra.items():
                setattr(record, key, value)
        return record


class NovaFormatter(logging.Formatter):
    """Nova-specific log formatter with rich text support."""
    
    def __init__(self, config):
        """Initialize formatter with config."""
        super().__init__()
        self.config = config
        self.datefmt = config.date_format
        
    def format(self, record: NovaLogRecord) -> str:
        """Format log record with phase and timing info."""
        # Format timestamp
        record.asctime = self.formatTime(record, self.datefmt)
        
        # Extract message and clean it
        message = record.getMessage()
        message = message.encode("utf-8", errors="replace").decode("utf-8")
        
        # Format level with color
        level_colors = {
            'DEBUG': '[dim]',
            'INFO': '[white]',
            'WARNING': '[yellow]',
            'ERROR': '[red]',
            'CRITICAL': '[red bold]'
        }
        level_color = level_colors.get(record.levelname, '')
        level_str = f"{level_color}[{record.levelname}][/]"
        
        # Build context information if enabled
        context_info = ""
        if self.config.include_context:
            # Add phase info if available
            if hasattr(record, 'phase') and record.phase:
                context_info += f"[cyan][{record.phase}][/cyan] "
            
            # Add handler info if available
            if hasattr(record, 'handler') and record.handler:
                context_info += f"[blue]({record.handler})[/blue] "
            
            # Add file info if available
            if hasattr(record, 'file_path') and record.file_path:
                context_info += f"[dim]<{record.file_path}>[/dim] "
            
            # Add timing info if available
            if hasattr(record, 'duration') and record.duration is not None:
                context_info += f"[yellow]({record.duration:.2f}s)[/yellow] "
            
            # Add progress info if available
            if hasattr(record, 'progress') and record.progress:
                context_info += f"[green][{record.progress}][/green] "
        
        # Build final message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            message = f"{message}\n{record.exc_text}"
        
        # Return formatted message
        return f"{record.asctime} {level_str} {context_info}{message}"


class LoggingManager:
    """Manage logging configuration."""
    
    def __init__(self, config):
        """Initialize logging manager."""
        self.config = config
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Set up logging configuration."""
        # Register NovaLogger as the logger class
        logging.setLoggerClass(NovaLogger)
        
        # Create log directory if needed
        if self.config.log_dir:
            log_dir = Path(os.path.expanduser(self.config.log_dir))
            log_dir.mkdir(parents=True, exist_ok=True)
        
        # Create formatters
        formatter = NovaFormatter(self.config)
        
        # Configure handlers
        handlers = []
        
        if "console" in self.config.handlers:
            console_handler = RichHandler(
                console=console,
                show_time=False,  # We'll handle this in our formatter
                show_path=False,  # We'll handle this in our formatter
                enable_link_path=True,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                tracebacks_width=100,
                tracebacks_extra_lines=3,
                tracebacks_theme='monokai',
                level=logging.WARNING,  # Set to WARNING to ensure summary is shown
                show_level=False,  # We'll handle this in our formatter
                omit_repeated_times=True,
                log_time_format="[%X]"
            )
            console_handler.setFormatter(formatter)
            handlers.append(console_handler)
        
        if "file" in self.config.handlers and self.config.log_dir:
            log_file = Path(os.path.expanduser(self.config.log_dir)) / f"nova_{datetime.now():%Y%m%d}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(formatter)
            file_handler.setLevel(self.config.file_level.upper())
            handlers.append(file_handler)
        
        # Configure root logger
        root = logging.getLogger()
        root.setLevel(logging.INFO)  # Set root logger to INFO to allow summary through
        
        # Remove existing handlers
        root.handlers = []
        
        # Add our handlers
        for handler in handlers:
            root.addHandler(handler)
        
        # Configure nova loggers
        for logger_name in logging.root.manager.loggerDict:
            if logger_name.startswith('nova'):
                logger = logging.getLogger(logger_name)
                
                # Set base level from config
                if 'summary' in logger_name:
                    logger.setLevel(logging.INFO)  # Set summary logger to INFO
                else:
                    logger.setLevel(self.config.level.upper())
                
                # Apply phase-specific level if applicable
                for phase, level in self.config.phase_levels.items():
                    if phase in logger_name:
                        logger.setLevel(level.upper())
                        break
                
                # Apply handler-specific level if applicable
                for handler_name, level in self.config.handler_levels.items():
                    if handler_name in logger_name:
                        logger.setLevel(level.upper())
                        break
                
                # Remove existing handlers
                logger.handlers = []
                
                # Add our handlers
                for handler in handlers:
                    logger.addHandler(handler)
                
                # Don't propagate to avoid duplicate messages
                logger.propagate = False


# Keep existing utility functions
def create_progress_bar() -> Progress:
    """Create a progress bar for tracking file processing."""
    return Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
    )


def print_summary(
    total_files: int,
    successful: int,
    failed: int,
    skipped: int,
    duration: float,
    unchanged: list,
    reprocessed: list,
    failures: list
) -> None:
    """Print processing summary."""
    logger = logging.getLogger("nova.summary")
    
    # Create a new console for the summary
    summary_console = Console(force_terminal=True)
    
    # Create summary table
    table = Table(title="\n📊 Processing Summary", title_style="bold cyan", border_style="cyan")
    table.add_column("Metric", style="bold white")
    table.add_column("Value", justify="right", style="green")
    
    # Add rows
    table.add_row("Total Files", str(total_files))
    table.add_row("Successful", f"[green]{str(successful)}[/green]")
    table.add_row("Failed", f"[red]{str(failed)}[/red]" if failed > 0 else str(failed))
    table.add_row("Skipped", f"[yellow]{str(skipped)}[/yellow]" if skipped > 0 else str(skipped))
    table.add_row("Unchanged", str(len(unchanged)))
    table.add_row("Reprocessed", str(len(reprocessed)))
    table.add_row("Duration", f"{duration:.2f}s")
    
    # Print table directly to console
    summary_console.print("\n")  # Add some spacing
    summary_console.print(table)
    
    # Log failures if any
    if failures:
        failure_msg = "\n❌ Failed Files:\n" + "━" * 80 + "\n"
        for file_path, error_msg in failures:
            failure_msg += f"• {Path(file_path).name}\n"
            failure_msg += f"  Error: {error_msg}\n\n"
        logger.error(failure_msg) 