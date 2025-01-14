"""Nova CLI main entry point.

This module provides the main CLI dispatcher for all nova commands. It
uses a plugin-based architecture to discover and register commands.
"""

import logging

import click
from rich.console import Console

from nova.cli.commands import (
    CleanProcessingCommand,
    CleanVectorsCommand,
    MonitorCommand,
    ProcessBearVectorsCommand,
    ProcessNotesCommand,
    ProcessVectorsCommand,
    SearchCommand,
)
from nova.cli.utils.command import NovaCommand
from nova.config import load_config

console = Console()


def setup_logging() -> None:
    """Set up logging configuration."""
    config = load_config()
    log_file = config.paths.logs_dir / "nova.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.FileHandler(log_file), logging.StreamHandler()],
    )


class NovaCLI:
    """Main CLI dispatcher for nova commands."""

    def __init__(self) -> None:
        """Initialize the CLI dispatcher."""
        self.commands: dict[str, type[NovaCommand]] = {}  # type: ignore
        self._register_commands()

    def _register_commands(self) -> None:
        """Register all available commands."""
        command_classes = [
            CleanProcessingCommand,
            CleanVectorsCommand,
            MonitorCommand,
            ProcessBearVectorsCommand,
            ProcessNotesCommand,
            ProcessVectorsCommand,
            SearchCommand,
        ]
        for cmd_class in command_classes:
            if not isinstance(cmd_class, type) or not issubclass(
                cmd_class, NovaCommand
            ):
                raise TypeError(f"Invalid command class: {cmd_class}")
            self.commands[cmd_class.name] = cmd_class  # type: ignore

    def create_cli(self) -> click.Group:
        """Create the CLI application.

        Returns:
            The Click command group for the CLI.
        """

        @click.group()
        def cli() -> None:
            """Nova - Your AI-powered note management system."""
            setup_logging()

        # Register all discovered commands
        for cmd_class in self.commands.values():
            cli.add_command(cmd_class().create_command())

        return cli


def main() -> None:
    """Main entry point for the nova CLI."""
    cli = NovaCLI().create_cli()
    cli()
