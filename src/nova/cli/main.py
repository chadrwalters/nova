"""Nova CLI main entry point.

This module provides the main CLI dispatcher for all nova commands. It
uses a plugin-based architecture to discover and register commands.
"""

import logging
import os
import sys

import click
from rich.console import Console
from rich.logging import RichHandler

from nova.cli.commands import (
    CleanProcessingCommand,
    CleanVectorsCommand,
    MonitorCommand,
    ProcessNotesCommand,
    ProcessVectorsCommand,
    SearchCommand,
)
from nova.cli.utils.command import NovaCommand
from nova.config import load_config
from nova.monitoring.persistent import PersistentMonitor
from nova.monitoring.session import SessionMonitor
from nova.vector_store.store import VectorStore

# Initialize console with stderr to avoid buffering issues
console = Console(stderr=True)


def setup_logging() -> None:
    """Set up logging configuration."""
    # Disable PostHog analytics
    os.environ["POSTHOG_DISABLED"] = "1"

    config = load_config()
    log_file = config.paths.logs_dir / "nova.log"
    log_file.parent.mkdir(parents=True, exist_ok=True)

    # Configure rich handler for console output
    rich_handler = RichHandler(
        console=console,
        show_path=False,
        omit_repeated_times=False,
        show_time=True,
        level=logging.INFO,  # Show INFO and above
    )

    # Configure file handler for log file
    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
    )
    file_handler.setLevel(logging.INFO)  # Log more details to file

    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)  # Set root logger to INFO
    root_logger.addHandler(rich_handler)
    root_logger.addHandler(file_handler)

    # Disable other handlers to prevent duplicate output
    logging.getLogger("sentence_transformers").handlers = []
    logging.getLogger("chromadb").handlers = []

    # Set specific loggers to WARNING
    for logger_name in [
        "sentence_transformers",
        "chromadb",
        "pypandoc",
        "html2text",
        "posthog",  # Silence PostHog analytics
    ]:
        logging.getLogger(logger_name).setLevel(logging.WARNING)

    # Set Nova loggers to INFO
    for logger_name in [
        "nova.cli",
        "nova.vector_store",
        "nova.monitoring",
    ]:
        logging.getLogger(logger_name).setLevel(logging.INFO)


class NovaCLI:
    """Main CLI dispatcher for nova commands."""

    def __init__(self) -> None:
        """Initialize the CLI dispatcher."""
        # Load configuration
        self.config = load_config()

        # Create shared components
        vector_store_dir = str(self.config.paths.vector_store_dir)
        self.vector_store = VectorStore(base_path=vector_store_dir)

        state_dir = self.config.paths.state_dir
        self.persistent_monitor = PersistentMonitor(base_path=state_dir)

        # Create shared session monitor
        self.session_monitor = SessionMonitor(
            vector_store=self.vector_store,
            log_manager=self.persistent_monitor,
            monitor=self.persistent_monitor,
            nova_dir=state_dir,
        )

        self.commands: dict[str, NovaCommand] = {}
        self._register_commands()

    def _register_commands(self) -> None:
        """Register all available commands."""
        command_classes = [
            CleanProcessingCommand,
            CleanVectorsCommand,
            MonitorCommand,
            ProcessNotesCommand,
            ProcessVectorsCommand,
            SearchCommand,
        ]

        for cmd_class in command_classes:
            cmd = cmd_class()
            if isinstance(cmd, MonitorCommand):
                cmd.set_dependencies(vector_store=self.vector_store)
            self.commands[cmd.name] = cmd

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
        for cmd_name, cmd in self.commands.items():
            cli.add_command(cmd.create_command())

        return cli


def main() -> None:
    """Main entry point for the nova CLI."""
    try:
        cli = NovaCLI().create_cli()
        cli()
    except Exception as e:
        console.print(f"[red]ERROR:[/red] {e!s}")
        sys.exit(1)
