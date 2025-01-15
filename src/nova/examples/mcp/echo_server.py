"""FastMCP Echo Server Example.

This is a minimal example of a FastMCP server that demonstrates the Model Context Protocol (MCP)
integration with Claude Desktop. It serves as a proof of concept for Nova's MCP capabilities.

Key Features:
- FastMCP-based server implementation
- Async tool handling
- Structured logging
- Clean error handling
- Claude Desktop integration

Configuration:
1. Install Nova with MCP dependencies
2. Configure Claude Desktop to use this server:
   - Server Type: Local Python Module
   - Module Path: nova.examples.mcp.echo_server
   - Working Directory: {Nova project root}

Usage:
    ```bash
    # From Nova project root
    uv run python -m nova.examples.mcp.echo_server
    ```

The server will start and Claude Desktop will automatically connect to it.
You can then use the 'echo' tool in Claude Desktop conversations.
"""
from pathlib import Path
from typing import Dict

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger

# Set up FastMCP logger
logger = get_logger(__name__)

# Create echo server
app = FastMCP(name="echo")

@app.tool(description="Echo back the message")
async def echo(message: str) -> Dict[str, str]:
    """Echo back the message.

    This is a simple tool that demonstrates FastMCP's tool registration and handling.
    It logs the incoming message and returns it wrapped in a response object.

    Args:
        message: The message to echo back

    Returns:
        Dict with the echoed message
    """
    logger.info(f"Echo tool called with message: {message}")
    response = {"message": f"Echo: {message}"}
    logger.info("Returning response", extra={"response": response})
    return response

if __name__ == "__main__":
    # Configure logging to .nova/logs
    log_dir = Path("~/.nova/logs").expanduser()
    log_dir.mkdir(parents=True, exist_ok=True)

    # Run the server
    logger.info("Starting FastMCP echo server")
    app.run()
