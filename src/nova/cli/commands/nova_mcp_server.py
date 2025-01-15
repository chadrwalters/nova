"""FastMCP Nova Server.

This server integrates with Claude Desktop to provide Nova's core functionality through MCP.
It exposes READ-ONLY tools for searching vectors and monitoring system health.

Key Features:
- FastMCP-based server implementation
- Vector store READ-ONLY access
- System monitoring
- Structured logging

IMPORTANT: This server is READ-ONLY. All write operations (processing notes,
creating vectors, cleaning) must be done through the CLI commands.

Configuration:
1. Install Nova with MCP dependencies
2. Configure Claude Desktop to use this server:
   - Server Type: Local Python Module
   - Module Path: nova.cli.commands.nova_mcp_server
   - Working Directory: {Nova project root}

Usage:
    ```bash
    # From Nova project root
    uv run python -m nova.cli.commands.nova_mcp_server
    ```

The server will start and Claude Desktop will automatically connect to it.
You can then use Nova's READ-ONLY tools in Claude Desktop conversations.
"""
from pathlib import Path
import asyncio
from typing import Dict, List, Optional, Any

from mcp.server.fastmcp import FastMCP
from mcp.server.fastmcp.utilities.logging import get_logger
from nova.vector_store.store import VectorStore, MODEL_NAME, BATCH_SIZE

# Set up FastMCP logger
logger = get_logger(__name__)

# Create Nova server
app = FastMCP(name="nova")

# Initialize vector store
vector_store = VectorStore(Path(".nova/vectors"))

@app.tool(description="Search the vector store for relevant notes")
async def search(query: str) -> List[Dict[str, Any]]:
    """Search the vector store for notes matching the query."""
    try:
        logger.info(f"Search tool called with query: {query}")
        results = await asyncio.to_thread(vector_store.search, query)
        logger.info("Returning search results", extra={"results": results})
        return results
    except Exception as e:
        logger.error(f"Search failed: {e}")
        return []

@app.tool(description="Monitor system health and stats")
async def monitor(command: str = "health") -> Dict[str, Any]:
    """Monitor system health and stats."""
    try:
        logger.info(f"Monitor tool called with command: {command}")
        if command == "health":
            data = {
                "status": "healthy",
                "vector_store": {
                    "path": str(vector_store._store_dir),
                    "exists": vector_store._store_dir.exists(),
                    "is_dir": vector_store._store_dir.is_dir(),
                    "permissions": oct(vector_store._store_dir.stat().st_mode)[-3:]
                }
            }
        else:
            collection = vector_store.collection
            count = collection.count()
            data = {
                "vector_store": {
                    "documents": count,
                    "model": MODEL_NAME,
                    "batch_size": BATCH_SIZE
                }
            }
        logger.info("Returning monitoring data", extra={"data": data})
        return data
    except Exception as e:
        logger.error(f"Monitoring failed: {e}")
        return {"status": "error", "error": str(e)}

if __name__ == "__main__":
    # Configure logging to .nova/logs
    log_dir = Path(".nova/logs")
    log_dir.mkdir(parents=True, exist_ok=True)

    # Run the server
    logger.info("Starting FastMCP Nova server")
    app.run()
