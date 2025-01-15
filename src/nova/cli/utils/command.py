"""Base command utilities for nova CLI.

This module provides the base command class and utilities for nova CLI
commands.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Coroutine

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


class NovaCommand(ABC):
    """Base class for all nova commands."""

    name: str
    help: str

    def run(self, **kwargs: Any) -> None:
        """Run the command with the given arguments.

        Args:
            **kwargs: Command arguments
        """
        if hasattr(self, "run_async"):
            asyncio.run(self.run_async(**kwargs))
        else:
            self._run_sync(**kwargs)

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

    @abstractmethod
    def create_command(self) -> click.Command:
        """Create the click command.

        Returns:
            The click command instance
        """
        pass

    def log_info(self, message: str) -> None:
        """Log an info message to the console.

        Args:
            message: The message to log.
        """
        console.print(f"[blue]INFO:[/blue] {message}")

    def log_error(self, message: str) -> None:
        """Log an error message to the console.

        Args:
            message: The message to log.
        """
        console.print(f"[red]ERROR:[/red] {message}")

    def log_success(self, message: str) -> None:
        """Log a success message to the console.

        Args:
            message: The message to log.
        """
        console.print(f"[green]SUCCESS:[/green] {message}")

    def log_warning(self, message: str) -> None:
        """Log a warning message to the console.

        Args:
            message: The message to log.
        """
        console.print(f"[yellow]WARNING:[/yellow] {message}")

    def create_progress(self) -> Progress:
        """Create a new progress bar.

        Returns:
            A new Progress instance.
        """
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        )
