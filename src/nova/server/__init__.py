"""Nova MCP Server Module.

This module implements the MCP (Model Control Protocol) server for Nova,
providing a standardized interface for AI model interactions through FastMCP.
"""

from nova.server.mcp import app as mcp_app

__version__ = "0.1.0"

__all__ = ["mcp_app"]
