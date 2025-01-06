"""Nova logging configuration."""
import logging
import os
import time
from datetime import datetime
from logging import LogRecord
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Type, TypeVar, Union

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

from ..config.settings import LoggingConfig

# Initialize console with force terminal
console = Console(force_terminal=True)

# Type variable for LogRecord subclasses
LR = TypeVar("LR", bound=LogRecord)


class NovaLogRecord(LogRecord):
    """Extended LogRecord with Nova-specific fields."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        """Initialize log record with Nova-specific fields."""
        super().__init__(*args, **kwargs)
        self.phase: Optional[str] = None
        self.handler: Optional[str] = None
        self.duration: Optional[float] = None
        self.context: Dict[str, Any] = {}
        self.file_path: Optional[Path] = None
        self.progress: Optional[str] = None


class NovaLogger(logging.Logger):
    """Extended Logger with Nova-specific methods."""

    def makeRecord(
        self,
        name: str,
        level: int,
        fn: str,
        lno: int,
        msg: object,
        args: Union[Sequence[Any], Mapping[str, Any]],
        exc_info: Union[BaseException, tuple[Any, Any, Any], None],
        func: Optional[str] = None,
        extra: Optional[Mapping[str, Any]] = None,
        sinfo: Optional[str] = None,
    ) -> NovaLogRecord:
        """Create a NovaLogRecord instead of LogRecord.

        Args:
            name: Logger name
            level: Log level
            fn: Filename
            lno: Line number
            msg: Log message
            args: Message arguments
            exc_info: Exception info
            func: Function name
            extra: Extra fields
            sinfo: Stack info

        Returns:
            A NovaLogRecord instance
        """
        record = NovaLogRecord(name, level, fn, lno, msg, args, exc_info, func, sinfo)
        if extra:
            for key, value in extra.items():
                setattr(record, key, value)
        return record


class NovaFormatter(logging.Formatter):
    """Nova-specific log formatter with rich text support."""

    def __init__(self, config: LoggingConfig) -> None:
        """Initialize formatter with config.

        Args:
            config: Logging configuration
        """
        super().__init__()
        self.config = config
        self.datefmt = config.date_format

    def format(self, record: LogRecord) -> str:
        """Format log record with phase and timing info.

        Args:
            record: Log record to format

        Returns:
            Formatted log message
        """
        # Format timestamp
        record.asctime = self.formatTime(record, self.datefmt)

        # Extract message and clean it
        message = record.getMessage()
        message = message.encode("utf-8", errors="replace").decode("utf-8")

        # Format level with color
        level_colors = {
            "DEBUG": "[dim]",
            "INFO": "[white]",
            "WARNING": "[yellow]",
            "ERROR": "[red]",
            "CRITICAL": "[red bold]",
        }
        level_color = level_colors.get(record.levelname, "")
        level_str = f"{level_color}[{record.levelname}][/]"

        # Build context information if enabled
        context_info = ""
        if self.config.include_context:
            # Add phase info if available
            if hasattr(record, "phase") and record.phase:
                context_info += f"[cyan][{record.phase}][/cyan] "

            # Add handler info if available
            if hasattr(record, "handler") and record.handler:
                context_info += f"[blue]({record.handler})[/blue] "

            # Add file info if available
            if hasattr(record, "file_path") and record.file_path:
                context_info += f"[dim]<{record.file_path}>[/dim] "

            # Add timing info if available
            if hasattr(record, "duration") and record.duration is not None:
                context_info += f"[yellow]({record.duration:.2f}s)[/yellow] "

            # Add progress info if available
            if hasattr(record, "progress") and record.progress:
                context_info += f"[green][{record.progress}][/green] "

        # Build final message
        if record.exc_info:
            if not record.exc_text:
                record.exc_text = self.formatException(record.exc_info)
            message = f"{message}\n{record.exc_text}"

        # Return formatted message
        return f"{record.asctime} {level_str} {context_info}{message}"


class LoggingManager:
    """Manager for Nova logging configuration."""

    def __init__(self, config: LoggingConfig) -> None:
        """Initialize logging manager.

        Args:
            config: Logging configuration
        """
        self.config = config
        self._setup_logging()

    def get_logger(self, name: str) -> NovaLogger:
        """Get a logger with Nova-specific configuration.

        Args:
            name: Logger name

        Returns:
            Configured NovaLogger instance
        """
        return logging.getLogger(name)  # type: ignore[return-value]

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
        handlers: List[logging.Handler] = []

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
                tracebacks_theme="monokai",
                level=logging.WARNING,  # Set to WARNING to ensure summary is shown
                show_level=False,  # We'll handle this in our formatter
                omit_repeated_times=True,
                log_time_format="[%X]",
            )
            console_handler.setFormatter(formatter)
            handlers.append(console_handler)

        if "file" in self.config.handlers and self.config.log_dir:
            log_file = (
                Path(os.path.expanduser(self.config.log_dir))
                / f"nova_{datetime.now():%Y%m%d}.log"
            )
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
            if logger_name.startswith("nova"):
                logger = logging.getLogger(logger_name)

                # Set base level from config
                if "summary" in logger_name:
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
    unchanged: List[Path],
    reprocessed: List[Path],
    failures: List[Dict[str, Any]],
) -> None:
    """Print processing summary.

    Args:
        total_files: Total number of files processed
        successful: Number of successfully processed files
        failed: Number of failed files
        skipped: Number of skipped files
        duration: Total processing duration in seconds
        unchanged: List of unchanged files
        reprocessed: List of reprocessed files
        failures: List of failure details
    """
    logger = logging.getLogger("nova.context_processor.summary")

    # Create a new console for the summary
    summary_console = Console(force_terminal=True)

    # Create summary table
    table = Table(
        title="\n📊 Processing Summary", title_style="bold cyan", border_style="cyan"
    )
    table.add_column("Metric", style="bold white")
    table.add_column("Value", style="white")

    # Add summary rows
    table.add_row("Total Files", str(total_files))
    table.add_row("Successful", f"[green]{successful}[/green]")
    table.add_row("Failed", f"[red]{failed}[/red]")
    table.add_row("Skipped", f"[yellow]{skipped}[/yellow]")
    table.add_row("Duration", f"{duration:.2f}s")

    # Print summary table
    summary_console.print(table)

    # Print unchanged files if any
    if unchanged:
        logger.info("\n📝 Unchanged Files:")
        for file in unchanged:
            logger.info(f"  • [dim]{file}[/dim]")

    # Print reprocessed files if any
    if reprocessed:
        logger.info("\n🔄 Reprocessed Files:")
        for file in reprocessed:
            logger.info(f"  • [yellow]{file}[/yellow]")

    # Print failures if any
    if failures:
        logger.error("\n❌ Failures:")
        for failure in failures:
            file_path = failure.get("file", "Unknown file")
            error = failure.get("error", "Unknown error")
            phase = failure.get("phase", "Unknown phase")
            logger.error(f"  • [red]{file_path}[/red]")
            logger.error(f"    Phase: {phase}")
            logger.error(f"    Error: {error}")


def log_duration(start_time: float) -> float:
    """Calculate and return duration since start time.

    Args:
        start_time: Start time in seconds

    Returns:
        Duration in seconds
    """
    return time.time() - start_time
