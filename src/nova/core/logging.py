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

console = Console()


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
    """Custom formatter for Nova logs."""
    
    def __init__(self, config: LoggingConfig):
        """Initialize formatter with configuration."""
        super().__init__(
            fmt=config.format,
            datefmt=config.date_format,
        )
        self.config = config
    
    def format(self, record: NovaLogRecord) -> str:
        """Format log record with phase and timing info."""
        # Format timestamp
        record.asctime = self.formatTime(record, self.datefmt)
        
        # Extract message and clean it
        message = record.getMessage()
        message = message.encode("utf-8", errors="replace").decode("utf-8")
        
        # Build context information if enabled
        context_info = ""
        if self.config.include_context:
            # Add phase info if available
            if hasattr(record, 'phase') and record.phase:
                context_info += f"[{record.phase}] "
            
            # Add handler info if available
            if hasattr(record, 'handler') and record.handler:
                context_info += f"({record.handler}) "
            
            # Add file info if available
            if hasattr(record, 'file_path') and record.file_path:
                context_info += f"<{record.file_path}> "
            
            # Add timing info if available
            if hasattr(record, 'duration') and record.duration is not None:
                context_info += f"({record.duration:.2f}s) "
            
            # Add progress info if available
            if hasattr(record, 'progress') and record.progress:
                context_info += f"[{record.progress}] "
            
            # Add any additional context
            if hasattr(record, 'context') and record.context:
                context_info += " ".join(f"{k}={v}" for k, v in record.context.items())
        
        # Build final message
        parts = [
            record.asctime,
            record.levelname,
            context_info,
            message
        ]
        
        return " ".join(p for p in parts if p)


class LoggingManager:
    """Manages logging configuration and setup."""
    
    def __init__(self, config: LoggingConfig):
        """Initialize logging manager.
        
        Args:
            config: Logging configuration
        """
        self.config = config
        self._setup_logging()
        
    def get_logger(self, name: str) -> logging.Logger:
        """Get a logger with the given name.
        
        Args:
            name: Logger name
            
        Returns:
            Logger instance
        """
        logger = logging.getLogger(name)
        
        # Set base level from config
        logger.setLevel(self.config.level)
        
        # Apply phase-specific level if applicable
        for phase, level in self.config.phase_levels.items():
            if phase in name:
                logger.setLevel(level)
                break
        
        # Apply handler-specific level if applicable
        for handler_name, level in self.config.handler_levels.items():
            if handler_name in name:
                logger.setLevel(level)
                break
        
        return logger
        
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
                show_time=True,
                show_path=True,
                enable_link_path=True,
                markup=True,
                rich_tracebacks=True,
                tracebacks_show_locals=True,
                level=self.config.console_level.upper()
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
        root.setLevel(self.config.level.upper())
        
        # Remove existing handlers
        root.handlers = []
        
        # Add our handlers
        for handler in handlers:
            root.addHandler(handler)
        
        # Configure nova loggers
        for logger_name in logging.root.manager.loggerDict:
            if logger_name.startswith('nova'):
                logger = logging.getLogger(logger_name)
                
                # Set base level
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
    
    # Create summary table
    table = Table(title="Processing Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    # Add rows
    table.add_row("Total Files", str(total_files))
    table.add_row("Successful", str(successful))
    table.add_row("Failed", str(failed))
    table.add_row("Skipped", str(skipped))
    table.add_row("Unchanged", str(len(unchanged)))
    table.add_row("Reprocessed", str(len(reprocessed)))
    table.add_row("Duration", f"{duration:.2f}s")
    
    # Log table
    logger.info("\n" + str(table))
    
    # Log failures if any
    if failures:
        failure_msg = "\nFailed Files:\n" + "━" * 80 + "\n"
        for file_path, error_msg in failures:
            failure_msg += f"• {Path(file_path).name}\n"
            failure_msg += f"  Error: {error_msg}\n\n"
        logger.error(failure_msg) 