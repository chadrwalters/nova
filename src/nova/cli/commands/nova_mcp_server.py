"""FastMCP Nova Server.

This server integrates with Claude Desktop to provide Nova's core
functionality through MCP. It exposes READ-ONLY tools for searching
vectors and monitoring system health.
"""

import asyncio
import atexit
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel

from nova.monitoring.logs import LogManager
from nova.monitoring.persistent import PersistentMonitor
from nova.monitoring.session import SessionMonitor
from nova.vector_store.store import VectorStore

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Create Nova server
app = FastMCP(name="nova")

# Initialize components
base_path = Path(".nova")
vector_store = VectorStore(str(base_path / "vectors"))
session_monitor = SessionMonitor(base_path)
persistent_monitor = PersistentMonitor(base_path)
log_manager = LogManager(str(base_path))


# Register cleanup on exit
@atexit.register
def cleanup():
    """Save session metrics on shutdown."""
    try:
        # Get final session metrics
        session_stats = session_monitor.get_session_stats()

        # Record in persistent storage
        persistent_monitor.record_session_end(session_stats)

        # Rotate logs if needed
        log_manager.rotate_logs()

        logger.info("Session ended, metrics saved")
    except Exception as e:
        logger.error("Failed to save session metrics: %s", str(e))


class SearchRequest(BaseModel):
    query: str
    limit: int = 5


class MonitorRequest(BaseModel):
    command: str = "health"
    subcommand: str | None = None
    days: int | None = None
    hours: int | None = None


@app.tool("search", description="Search for notes in the vector store")
async def search(query: str, limit: int = 5) -> dict[str, Any]:
    """Search the vector store for relevant notes."""
    try:
        start_time = datetime.now()

        # Search for similar documents
        results = await asyncio.to_thread(vector_store.search, query, limit=limit)

        # Record query metrics
        query_time = (datetime.now() - start_time).total_seconds()
        session_monitor.record_query(query_time)

        # Return empty results with message for no matches
        if not results:
            return {
                "results": [],
                "count": 0,
                "query": query,
                "query_time": query_time,
                "message": "No results found",
            }

        formatted_results = []
        for i, result in enumerate(results, 1):
            metadata = result["metadata"]
            score = min(100.0, result["score"])  # Cap at 100%
            text = result["text"]

            formatted_result = {
                "rank": i,
                "score": score,
                "heading": metadata.get("heading_text", "No heading"),
                "tags": metadata.get("tags", "[]"),
                "content": text[:200] + "..." if len(text) > 200 else text,
                **metadata,  # Include all other metadata
            }
            formatted_results.append(formatted_result)

        return {
            "results": formatted_results,
            "count": len(formatted_results),
            "query": query,
            "query_time": query_time,
        }

    except Exception as e:
        error_msg = f"Search failed: {e!s}"
        logger.error(error_msg)
        session_monitor.record_error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


@app.tool(description="Monitor system health and stats")
async def monitor(
    command: str = "health",
    subcommand: str | None = None,
    days: int | None = None,
    hours: int | None = None,
) -> dict[str, Any]:
    """Monitor system health and stats."""
    try:
        if command == "health":
            # Get both session and persistent health data
            session_health = session_monitor.check_health()
            system_health = persistent_monitor.get_system_health()

            return {"session": session_health, "system": system_health}

        elif command == "stats":
            # Get session stats
            session_stats = session_monitor.get_session_stats()

            # Get performance trends
            trends = persistent_monitor.get_performance_trends(days=days or 7)

            return {"session": session_stats, "trends": trends}

        elif command == "logs":
            # Get log analysis
            log_stats = log_manager.get_stats()
            recent_logs = log_manager.tail_logs(n=100)

            return {"stats": log_stats, "recent": recent_logs}

        elif command == "errors":
            # Get error summary
            error_summary = persistent_monitor.get_error_summary(days=days or 7)
            recent_logs = log_manager.tail_logs(n=100)

            return {"summary": error_summary, "recent": recent_logs}

        else:
            raise ValueError(f"Unknown monitor command: {command}")

    except Exception as e:
        error_msg = f"Monitoring failed: {e!s}"
        logger.error(error_msg)
        session_monitor.record_error(error_msg)
        raise HTTPException(status_code=500, detail=error_msg)


if __name__ == "__main__":
    # Ensure required directories exist
    base_path.mkdir(exist_ok=True)
    (base_path / "vectors").mkdir(exist_ok=True)
    (base_path / "logs").mkdir(exist_ok=True)
    (base_path / "metrics").mkdir(exist_ok=True)

    # Start the server
    logger.info("Starting Nova MCP server")
    app.run()
