"""Nova CLI main entry point.

This module provides the main CLI dispatcher for all nova commands. It
uses a plugin-based architecture to discover and register commands.
"""

import logging
import sys

import click
from rich.console import Console
from rich.logging import RichHandler

from nova.cli.commands import (
    CleanProcessingCommand,
    CleanVectorsCommand,
    MonitorCommand,
    ProcessBearVectorsCommand,
    ProcessNotesCommand,
    ProcessVectorsCommand,
    SearchCommand,
    StartMCPCommand,
)
from nova.cli.utils.command import NovaCommand
from nova.config import load_config

# Initialize console with stderr to avoid buffering issues
console = Console(stderr=True)


def setup_logging() -> None:
    """Set up logging configuration."""
    print("DEBUG: Setting up logging")  # Debug print
    config = load_config()
    log_file = config.paths.logs_dir / "nova.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure rich handler for console output
    rich_handler = RichHandler(
        console=console,
        show_path=False,
        omit_repeated_times=False,
        show_time=True,
    )

    # Configure file handler for log file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)

    # Disable other handlers to prevent duplicate output
    logging.getLogger("sentence_transformers").handlers = []
    logging.getLogger("chromadb").handlers = []
    print("DEBUG: Logging setup complete")  # Debug print


class NovaCLI:
    """Main CLI dispatcher for nova commands."""

    def __init__(self) -> None:
        """Initialize the CLI dispatcher."""
        print("DEBUG: Initializing NovaCLI")  # Debug print
        self.commands: dict[str, type[NovaCommand]] = {}  # type: ignore
        self._register_commands()

    def _register_commands(self) -> None:
        """Register all available commands."""
        print("DEBUG: Registering commands")  # Debug print
        command_classes = [
            CleanProcessingCommand,
            CleanVectorsCommand,
            MonitorCommand,
            ProcessBearVectorsCommand,
            ProcessNotesCommand,
            ProcessVectorsCommand,
            SearchCommand,
            StartMCPCommand,
        ]
        for cmd_class in command_classes:
            print(f"DEBUG: Registering command class: {cmd_class.__name__}")  # Debug print
            if not isinstance(cmd_class, type) or not issubclass(cmd_class, NovaCommand):
                raise TypeError(f"Invalid command class: {cmd_class}")
            self.commands[cmd_class.name] = cmd_class  # type: ignore
        print("DEBUG: Command registration complete")  # Debug print

    def create_cli(self) -> click.Group:
        """Create the CLI application.

        Returns:
            The Click command group for the CLI.
        """
        print("DEBUG: Creating CLI")  # Debug print

        @click.group()
        def cli() -> None:
            """Nova - Your AI-powered note management system."""
            print("DEBUG: Running CLI setup")  # Debug print
            setup_logging()

        # Register all discovered commands
        for cmd_name, cmd_class in self.commands.items():
            print(f"DEBUG: Adding command to CLI: {cmd_name}")  # Debug print
            cli.add_command(cmd_class().create_command())

        print("DEBUG: CLI creation complete")  # Debug print
        return cli


def main() -> None:
    """Main entry point for the nova CLI."""
    print("DEBUG: Starting main")  # Debug print
    try:
        cli = NovaCLI().create_cli()
        print("DEBUG: Running CLI")  # Debug print
        cli()
    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e!s}")
        sys.exit(1)
