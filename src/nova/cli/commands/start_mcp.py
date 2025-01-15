"""Start MCP server command."""

import click
from typing import Any, cast

from nova.cli.utils.command import NovaCommand
from nova.cli.commands.nova_mcp_server import app as nova_mcp

class StartMCPCommand(NovaCommand):
    """Start MCP server command."""

    name = "start-mcp"

    def run(self, **kwargs: Any) -> None:
        """Run the command."""
        nova_mcp(**kwargs)

    def create_command(self) -> click.Command:
        """Create the start-mcp command."""
        return cast(click.Command, nova_mcp)
