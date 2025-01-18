"""Base command utilities for nova CLI.

This module provides the base command class and utilities for nova CLI
commands.
"""

import asyncio
import inspect
import logging
from abc import ABC
from collections.abc import Callable
from typing import Any, TypeVar

import click
import psutil
from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TaskProgressColumn,
    TextColumn,
    TimeRemainingColumn,
)

from nova.cli.utils.errors import RebuildError
from nova.config import load_config
from nova.vector_store.store import VectorStore

# Initialize console with stderr to avoid buffering issues
console = Console(stderr=True)

# Type variable for click command function
F = TypeVar("F", bound=Callable[..., Any])


class NovaCommand(ABC):
    """Base class for all nova commands."""

    name: str
    help: str

    def __init__(self) -> None:
        """Initialize the base command."""
        self.config = load_config()

    def set_dependencies(self, vector_store: VectorStore | None = None) -> None:
        """Set command dependencies.

        Args:
            vector_store: Optional vector store instance
        """
        pass  # Override in subclasses that need dependencies

    def run(self, **kwargs: Any) -> None:
        """Run the command with the given arguments.

        Args:
            **kwargs: Command arguments
        """
        try:
            # Check for required arguments
            if hasattr(self, "_run_sync"):
                sig = inspect.signature(self._run_sync)
                required_args = {
                    name: param
                    for name, param in sig.parameters.items()
                    if param.default == inspect.Parameter.empty and name != "kwargs"
                }
                missing_args = [name for name in required_args if name not in kwargs]
                if missing_args:
                    raise TypeError(
                        f"{self.__class__.__name__}.run() missing {len(missing_args)} required positional argument{'s' if len(missing_args) > 1 else ''}: {', '.join(repr(arg) for arg in missing_args)}"
                    )

                self._run_sync(**kwargs)
            elif hasattr(self, "run_async"):
                asyncio.run(self.run_async(**kwargs))
            else:
                raise NotImplementedError("Command must implement either _run_sync or run_async")
        except Exception as e:
            self.log_error(f"Command failed: {e!s}")
            raise

    def _run_sync(self, **kwargs: Any) -> None:
        """Run the command synchronously.

        Args:
            **kwargs: Command arguments
        """
        pass

    async def run_async(self, **kwargs: Any) -> None:
        """Run the command asynchronously.

        Args:
            **kwargs: Command arguments
        """
        pass

    def create_command(self) -> click.Command:
        """Create the click command.

        Returns:
            The click command instance
        """

        @click.command(name=self.name, help=self.help)
        def command(**kwargs: Any) -> None:
            """Execute command with given arguments."""
            self.run(**kwargs)

        return command

    def log_info(self, message: str) -> None:
        """Log an info message to the console.

        Args:
            message: The message to log.
        """
        logging.info(f"[INFO] {message}")

    def log_error(self, message: str) -> None:
        """Log an error message to the console.

        Args:
            message: The message to log.
        """
        logging.error(f"[ERROR] {message}")

    def log_success(self, message: str) -> None:
        """Log a success message to the console.

        Args:
            message: The message to log.
        """
        logging.info(f"[SUCCESS] {message}")

    def log_warning(self, message: str) -> None:
        """Log a warning message to the console.

        Args:
            message: The message to log.
        """
        logging.warning(f"[WARNING] {message}")

    def create_progress(self) -> Progress:
        """Create a new progress bar with enhanced features.

        Returns:
            A new Progress instance with time remaining, memory usage, and processing rate.
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            MofNCompleteColumn(),
            TimeRemainingColumn(),
            TextColumn("[cyan]{task.fields[rate]}/s[/cyan]"),
            TextColumn("[yellow]Mem: {task.fields[memory]}MB[/yellow]"),
            console=console,
            expand=True,
            refresh_per_second=10,
        )

    def update_progress_stats(self, progress: Progress, task_id: TaskID, advance: int = 1) -> None:
        """Update progress statistics including processing rate and memory
        usage.

        Args:
            progress: The Progress instance to update
            task_id: The ID of the task to update
            advance: Number of steps to advance (default: 1)
        """
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        task = progress.tasks[task_id]
        elapsed = task.elapsed if task.elapsed is not None else 0.1
        rate = task.completed / elapsed if elapsed > 0 else 0

        progress.update(
            task_id,
            advance=advance,
            memory=f"{memory_mb:.1f}",
            rate=f"{rate:.1f}",
        )

    def handle_error(self, error: Exception) -> None:
        """Handle a rebuild error.

        Args:
            error: The error to handle
        """
        if isinstance(error, RebuildError):
            self.log_error(str(error))
            if error.is_recoverable:
                self.log_warning(f"Recovery hint: {error.recovery_hint}")
        else:
            self._handle_recoverable_error(error)

    def _handle_recoverable_error(self, error: Exception) -> bool:
        """Handle generic recoverable errors.

        Args:
            error: The error to handle

        Returns:
            True if error was recovered from, False otherwise
        """
        if isinstance(error, FileNotFoundError):
            self.log_warning(f"File not found: {error.filename}")
            self.log_info("Creating missing directories...")
            return True

        if isinstance(error, PermissionError):
            self.log_warning(f"Permission error: {error}")
            self.log_info("Please check file permissions and try again")
            return False

        if isinstance(error, TimeoutError):
            self.log_warning("Operation timed out")
            self.log_info("You can retry the operation")
            return True

        self.log_error(str(error))
        return False
