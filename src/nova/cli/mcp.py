"""MCP server command for Nova CLI."""

import logging
from pathlib import Path

import click
from rich.console import Console
from rich.logging import RichHandler

from nova.server.server import NovaServer
from nova.server.types import ServerConfig

# Configure logging
console = Console()
log_dir = Path(".nova/logs")
log_dir.mkdir(parents=True, exist_ok=True)

log_file = log_dir / "mcp-server.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, rich_tracebacks=True), logging.FileHandler(log_file)],
)

logger = logging.getLogger("nova.mcp")


@click.command()
@click.option("--host", default="localhost", help="Host to bind server to")
@click.option("--port", default=8765, help="Port to bind server to")
@click.option("--max-connections", default=10, help="Maximum number of concurrent connections")
def mcp(host: str, port: int, max_connections: int) -> None:
    """Start the Nova MCP server.

    This provides an MCP-compatible interface for Claude to interact
    with Nova's functionality. The server will start on the specified
    host and port (default: localhost:8765).
    """
    try:
        # Create and start Nova server
        config = ServerConfig(host=host, port=port, max_connections=max_connections)

        logger.info("Starting Nova server...")
        server = NovaServer(config)
        server.start()

        # Keep server running
        logger.info(f"Nova MCP server running at {host}:{port}")
        logger.info("Press Ctrl+C to stop")

        # Block until interrupted
        try:
            import asyncio

            asyncio.get_event_loop().run_forever()
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            server.stop()

    except Exception as e:
        logger.exception("Failed to start MCP server")
        raise click.ClickException(str(e))


if __name__ == "__main__":
    mcp()
