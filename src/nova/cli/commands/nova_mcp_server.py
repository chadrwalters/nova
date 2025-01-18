"""Nova MCP Server.

This server provides Nova's core functionality through MCP. It exposes
tools for searching vectors and monitoring system health.
"""

import asyncio
import atexit
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rich.console import Console
from rich.logging import RichHandler

from nova.monitoring.logs import LogManager
from nova.monitoring.persistent import PersistentMonitor
from nova.monitoring.session import SessionMonitor
from nova.vector_store.store import VectorStore

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.WARNING)

# Initialize console
console = Console(stderr=True)

# Configure root logger
logging.basicConfig(
    level=logging.WARNING,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, show_path=False, show_time=False)]
)

# Disable noisy third-party loggers
logging.getLogger("chromadb").setLevel(logging.WARNING)
logging.getLogger("sentence_transformers").setLevel(logging.WARNING)
logging.getLogger("nova.cli").setLevel(logging.WARNING)
logging.getLogger("nova.vector_store").setLevel(logging.WARNING)
logging.getLogger("nova.monitoring").setLevel(logging.WARNING)

# Create Nova server
app = FastAPI(title="Nova MCP", description="Nova Master Control Program", version="0.1.0")

# Initialize components
base_path = Path(".nova")
vector_store = VectorStore(base_path=str(base_path / "vectors"))
session_monitor = SessionMonitor(vector_store=vector_store)
persistent_monitor = PersistentMonitor(base_path)
log_manager = LogManager(str(base_path))

# Register cleanup on exit
@atexit.register
def cleanup() -> None:
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

def main() -> None:
    """Run the MCP server."""
    # Ensure required directories exist
    base_path.mkdir(exist_ok=True)
    (base_path / "vectors").mkdir(exist_ok=True)
    (base_path / "logs").mkdir(exist_ok=True)
    (base_path / "metrics").mkdir(exist_ok=True)

    # Start the server
    logger.info("Starting Nova MCP server")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)

class SearchRequest(BaseModel):
    """Search request model."""

    query: str
    limit: int = 5


@app.post("/search")
async def search(request: SearchRequest) -> dict[str, Any]:
    """Search the vector store for relevant notes."""
    try:
        start_time = datetime.now()
        results = vector_store.search(request.query, limit=request.limit)
        end_time = datetime.now()
        processing_time = (end_time - start_time).total_seconds()

        # Track search as a rebuild operation
        session_monitor.track_rebuild_progress(len(results))
        session_monitor.update_rebuild_progress(len(results), processing_time)

        return {
            "results": results,
            "total": len(results),
            "query": request.query,
            "processing_time": processing_time,
        }

    except Exception as e:
        logger.error("Search failed: %s", str(e))
        session_monitor.record_rebuild_error(str(e))
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
async def health() -> dict[str, Any]:
    """Get system health status."""
    try:
        # Get session metrics
        session_stats = session_monitor.get_session_stats()

        # Get log stats
        log_stats = log_manager.get_stats()

        return {
            "status": "healthy",
            "session": session_stats,
            "logs": log_stats,
        }

    except Exception as e:
        logger.error("Health check failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))
