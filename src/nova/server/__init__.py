"""Nova server initialization.

This module provides the Nova server implementation using FastAPI.
"""

from nova.server.mcp import app as mcp_app

__version__ = "0.1.0"

__all__ = ["mcp_app"]
