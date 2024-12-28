"""Nova logging configuration."""
import logging
import time
from typing import Dict, Optional
from pathlib import Path

from rich.console import Console
from rich.logging import RichHandler
from rich.progress import Progress, SpinnerColumn, TextColumn, TimeElapsedColumn
from rich.table import Table

console = Console()


class NovaFormatter(logging.Formatter):
    """Custom formatter for Nova logs."""
    
    def __init__(self):
        """Initialize formatter with default format."""
        super().__init__(
            fmt="%(asctime)s [%(levelname)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    
    def format(self, record: logging.LogRecord) -> str:
        """Format log record with phase and timing info.
        
        Args:
            record: Log record to format.
            
        Returns:
            Formatted log message.
        """
        # Format timestamp
        record.asctime = self.formatTime(record, self.datefmt)
        
        # Extract message and clean it
        message = record.getMessage()
        message = message.encode("utf-8", errors="replace").decode("utf-8")
        
        # Get phase info if available
        phase = getattr(record, "phase", "")
        phase_info = f"[{phase}] " if phase else ""
        
        # Get timing info if available
        duration = getattr(record, "duration", None)
        timing_info = f" ({duration:.2f}s)" if duration else ""
        
        # Get progress info if available
        progress = getattr(record, "progress", "")
        progress_info = f" [{progress}]" if progress else ""
        
        # Build message parts
        parts = [
            f"{record.asctime}",
            f"{record.levelname:8}",
            phase_info,
            message,
            timing_info,
            progress_info,
        ]
        
        # Filter out empty parts and join
        return " ".join(p for p in parts if p)


def create_progress_bar() -> Progress:
    """Create a progress bar for tracking file processing.
    
    Returns:
        Progress bar instance.
    """
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
    unchanged: int,
    reprocessed: int,
    duration: float,
    failures: list
) -> None:
    """Print processing summary.
    
    Args:
        total_files: Total number of files processed
        successful: Number of successfully processed files
        failed: Number of failed files
        skipped: Number of skipped files
        unchanged: Number of unchanged files
        reprocessed: Number of reprocessed files
        duration: Processing duration in seconds
        failures: List of (file_path, error_message) tuples
    """
    # Print existing summary table
    print("\n   Processing Summary")
    print("┏━━━━━━━━━━━━━┳━━━━━━━━┓")
    print("┃ Metric      ┃  Value ┃")
    print("┡━━━━━━━━━━━━━╇━━━━━━━━┩")
    print(f"│ Total Files │ {total_files:>6} │")
    print(f"│ Successful  │ {successful:>6} │")
    print(f"│ Failed      │ {failed:>6} │")
    print(f"│ Skipped     │ {skipped:>6} │")
    print(f"│ Unchanged   │ {unchanged:>6} │")
    print(f"│ Reprocessed │ {reprocessed:>6} │")
    print(f"│ Duration    │ {duration:.2f}s │")
    print("└─────────────┴────────┘")

    # Add failure details if there are any failures
    if failures:
        print("\nFailed Files:")
        print("━" * 80)
        for file_path, error_msg in failures:
            # Get just the filename from the path
            filename = Path(file_path).name
            print(f"• {filename}")
            print(f"  Error: {error_msg}")
            print() 