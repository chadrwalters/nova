"""Nova MCP Server.

This server integrates with Claude Desktop and uses FastMCP to expose Nova's features
as tools that Claude can use. It wraps our CLI commands in an async-friendly way
and provides structured logging and error handling.
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
import asyncio

from mcp.server.fastmcp import FastMCP

from nova.cli.commands.process_notes import ProcessNotesCommand
from nova.cli.commands.search import SearchCommand
from nova.cli.commands.monitor import MonitorCommand
from nova.cli.commands.clean_processing import CleanProcessingCommand
from nova.cli.commands.clean_vectors import CleanVectorsCommand
from nova.logging import get_component_logger, log_tool_call, configure_logging
from nova.vector_store.store import VectorStore

# Set up Nova logger
logger = get_component_logger(__name__)

# Create Nova MCP server
app = FastMCP(name="nova")

# Initialize components
vector_store = VectorStore(Path(".nova/vectors"))

# Initialize CLI commands
process_notes = ProcessNotesCommand()
search = SearchCommand()
monitor = MonitorCommand()
clean_processing = CleanProcessingCommand()
clean_vectors = CleanVectorsCommand()

@app.tool(description="Process notes with format detection and conversion")
async def process_notes_tool(
    input_dir: Optional[str] = None,
    output_dir: Optional[str] = None
) -> Dict[str, Any]:
    """Process notes with format detection and conversion."""
    log_tool_call(logger, "process_notes", {"input_dir": input_dir, "output_dir": output_dir})

    try:
        # Convert string paths to Path objects
        input_path = Path(input_dir) if input_dir else None
        output_path = Path(output_dir) if output_dir else None

        # Run the command
        await process_notes.run_async(input_dir=input_path, output_dir=output_path)
        return {"status": "success", "message": "Notes processed successfully"}
    except Exception as e:
        logger.error("Failed to process notes", exc_info=e, extra={
            "input_dir": input_dir,
            "output_dir": output_dir
        })
        raise

@app.tool(description="Search through vector embeddings")
async def search_tool(
    query: str,
    vector_dir: Optional[str] = None,
    limit: int = 5
) -> Dict[str, Any]:
    """Search through vector embeddings."""
    log_tool_call(logger, "search", {
        "query": query,
        "vector_dir": vector_dir,
        "limit": limit
    })

    try:
        # Run search in a thread to avoid blocking
        results = await asyncio.to_thread(vector_store.search, query, limit)

        # Format results for response
        formatted_results = []
        for result in results:
            metadata = result["metadata"]
            distance = result.get("distance", 0.0)
            # Convert cosine distance to similarity score (0-100%)
            similarity = max(0.0, min(1.0, (2.0 - distance) / 2.0)) * 100

            formatted_results.append({
                "title": metadata.get("title", "Untitled"),
                "similarity": similarity,
                "tags": metadata.get("tags", []),
                "date": metadata.get("date", "Unknown"),
                "content": metadata.get("content", "")[:200] + "...",  # First 200 chars
                "id": result.get("id")
            })

        return {
            "status": "success",
            "results": formatted_results,
            "count": len(formatted_results),
            "query": query
        }
    except Exception as e:
        logger.error("Failed to search vectors", exc_info=e, extra={
            "query": query,
            "vector_dir": vector_dir,
            "limit": limit
        })
        raise

@app.tool(description="Monitor system health, stats, and logs")
async def monitor_tool(subcommand: str = "health") -> Dict[str, Any]:
    """Monitor system health, stats, and logs."""
    log_tool_call(logger, "monitor", {"subcommand": subcommand})

    try:
        # Run the command
        await monitor.run_async(subcommand=subcommand)

        # Add vector store stats for health/stats commands
        if subcommand in ["health", "stats"]:
            # Get vector store metadata in a thread
            metadata = await asyncio.to_thread(vector_store.get_metadata)
            return {
                "status": "success",
                "message": f"Monitor {subcommand} completed",
                "vector_store": metadata
            }

        return {"status": "success", "message": f"Monitor {subcommand} completed"}
    except Exception as e:
        logger.error("Failed to run monitor command", exc_info=e, extra={
            "subcommand": subcommand
        })
        raise

@app.tool(description="Clean the processing directory")
async def clean_processing_tool(force: bool = False) -> Dict[str, Any]:
    """Clean the processing directory."""
    log_tool_call(logger, "clean_processing", {"force": force})

    try:
        # Run the command
        await clean_processing.run_async(force=force)
        return {"status": "success", "message": "Processing directory cleaned"}
    except Exception as e:
        logger.error("Failed to clean processing directory", exc_info=e, extra={
            "force": force
        })
        raise

@app.tool(description="Clean the vector store")
async def clean_vectors_tool(force: bool = False) -> Dict[str, Any]:
    """Clean the vector store."""
    log_tool_call(logger, "clean_vectors", {"force": force})

    try:
        # Run the command
        await clean_vectors.run_async(force=force)

        # Clean up vector store in a thread
        if force:
            await asyncio.to_thread(vector_store.cleanup)

        return {"status": "success", "message": "Vector store cleaned"}
    except Exception as e:
        logger.error("Failed to clean vector store", exc_info=e, extra={
            "force": force
        })
        raise

if __name__ == "__main__":
    # Configure logging
    configure_logging()

    # Run the server
    logger.info("Starting Nova MCP server")
    app.run()

