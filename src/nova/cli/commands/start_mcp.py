"""Start MCP server command."""

from typing import Any, cast

import click

from nova.cli.utils.command import NovaCommand


class StartMCPCommand(NovaCommand):
    """Start MCP server command."""

    name = "start-mcp"

    def run(self, **kwargs: Any) -> None:
        """Run the command."""
        # Import here to avoid circular imports
        from nova.cli.commands.nova_mcp_server import app as nova_mcp

        nova_mcp(**kwargs)

    def create_command(self) -> click.Command:
        """Create the start-mcp command."""
        # Import here to avoid circular imports
        from nova.cli.commands.nova_mcp_server import app as nova_mcp

        return cast(click.Command, nova_mcp)
