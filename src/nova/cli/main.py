"""Nova CLI main entry point.

This module provides the main CLI dispatcher for all nova commands. It
uses a plugin-based architecture to discover and register commands.
"""

import importlib
import pkgutil

import click
from rich.console import Console

from nova.cli import commands
from nova.cli.utils.command import NovaCommand

console = Console()


class NovaCLI:
    """Main CLI dispatcher for nova commands."""

    def __init__(self) -> None:
        """Initialize the CLI dispatcher."""
        self.commands: dict[str, type[NovaCommand]] = {}
        self._discover_commands()

    def _discover_commands(self) -> None:
        """Discover and register all available commands."""
        for _, name, _ in pkgutil.iter_modules(commands.__path__):
            module = importlib.import_module(f"nova.cli.commands.{name}")
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, NovaCommand)
                    and attr != NovaCommand
                ):
                    self.commands[attr.name] = attr

    def create_cli(self) -> click.Group:
        """Create the CLI application.

        Returns:
            The Click command group for the CLI.
        """

        @click.group()
        def cli() -> None:
            """Nova - Your AI-powered note management system."""
            pass

        # Register all discovered commands
        for cmd_class in self.commands.values():
            cli.add_command(cmd_class().create_command())

        return cli


def main() -> None:
    """Main entry point for the nova CLI."""
    cli = NovaCLI().create_cli()
    cli()
