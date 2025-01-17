"""Base command utilities for nova CLI.

This module provides the base command class and utilities for nova CLI
commands.
"""

import asyncio
import inspect
from abc import ABC, abstractmethod
from typing import Any

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

# Initialize console with stderr to avoid buffering issues
console = Console(stderr=True)


class NovaCommand(ABC):
    """Base class for all nova commands."""

    name: str
    help: str

    def __init__(self) -> None:
        """Initialize the base command."""
        print("DEBUG: Initializing NovaCommand base class")  # Debug print

    def run(self, **kwargs: Any) -> None:
        """Run the command with the given arguments.

        Args:
            **kwargs: Command arguments
        """
        print(f"DEBUG: NovaCommand.run called with kwargs: {kwargs}")  # Debug print
        try:
            # Check for required arguments
            if hasattr(self, "_run_sync"):
                sig = inspect.signature(self._run_sync)
                required_args = {
                    name: param
                    for name, param in sig.parameters.items()
                    if param.default == inspect.Parameter.empty
                }
                missing_args = [name for name in required_args if name not in kwargs]
                if missing_args:
                    raise TypeError(
                        f"{self.__class__.__name__}.run() missing {len(missing_args)} required positional argument{'s' if len(missing_args) > 1 else ''}: {', '.join(repr(arg) for arg in missing_args)}"
                    )

                print("DEBUG: Running sync command")  # Debug print
                self._run_sync(**kwargs)
            elif hasattr(self, "run_async"):
                print("DEBUG: Running async command")  # Debug print
                asyncio.run(self.run_async(**kwargs))
            else:
                print("DEBUG: No run method found")  # Debug print
                raise NotImplementedError("Command must implement either _run_sync or run_async")
        except Exception as e:
            print(f"DEBUG: Command failed with error: {e}")  # Debug print
            self.log_error(f"Command failed: {e!s}")
            raise

    def _run_sync(self, **kwargs: Any) -> None:
        """Run the command synchronously.

        Args:
            **kwargs: Command arguments
        """
        print("DEBUG: NovaCommand._run_sync called")  # Debug print
        pass

    async def run_async(self, **kwargs: Any) -> None:
        """Run the command asynchronously.

        Args:
            **kwargs: Command arguments
        """
        print("DEBUG: NovaCommand.run_async called")  # Debug print
        pass

    @abstractmethod
    def create_command(self) -> click.Command:
        """Create the click command.

        Returns:
            The click command instance
        """
        print("DEBUG: NovaCommand.create_command called")  # Debug print
        pass

    def log_info(self, message: str) -> None:
        """Log an info message to the console.

        Args:
            message: The message to log.
        """
        print(f"DEBUG: NovaCommand.log_info called with message: {message}")  # Debug print
        console.print(f"[blue]INFO:[/blue] {message}", highlight=False)

    def log_error(self, message: str) -> None:
        """Log an error message to the console.

        Args:
            message: The message to log.
        """
        print(f"DEBUG: NovaCommand.log_error called with message: {message}")  # Debug print
        console.print(f"[red]ERROR:[/red] {message}", highlight=False)

    def log_success(self, message: str) -> None:
        """Log a success message to the console.

        Args:
            message: The message to log.
        """
        print(f"DEBUG: NovaCommand.log_success called with message: {message}")  # Debug print
        console.print(f"[green]SUCCESS:[/green] {message}", highlight=False)

    def log_warning(self, message: str) -> None:
        """Log a warning message to the console.

        Args:
            message: The message to log.
        """
        print(f"DEBUG: NovaCommand.log_warning called with message: {message}")  # Debug print
        console.print(f"[yellow]WARNING:[/yellow] {message}", highlight=False)

    def create_progress(self) -> Progress:
        """Create a new progress bar.

        Returns:
            A new Progress instance.
        """
        print("DEBUG: NovaCommand.create_progress called")  # Debug print
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
