"""MCP Echo Server Example.

This is a minimal example of a server that demonstrates the Model Context Protocol (MCP)
integration. It provides a simple echo tool that returns the input text.

Features:
- MCP-based server implementation
- Basic tool registration
- Error handling
- Logging configuration
"""

import logging
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from rich.console import Console
from rich.logging import RichHandler

# Set up logging
logger = logging.getLogger(__name__)

# Initialize console
console = Console(stderr=True)

# Configure root logger
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(console=console, show_path=False, show_time=False)]
)

# Create server
app = FastAPI(title="Echo Server", description="Simple MCP echo server", version="0.1.0")

class EchoRequest(BaseModel):
    """Echo request model."""

    text: str


@app.post("/echo")
async def echo(request: EchoRequest) -> dict[str, Any]:
    """Echo the input text back.

    This is a simple tool that demonstrates MCP's tool registration and handling.
    It takes a text input and returns it unmodified.

    Args:
        request: The echo request containing the text to echo

    Returns:
        Dict containing the echoed text and metadata
    """
    try:
        logger.info("Echoing text: %s", request.text)
        return {
            "text": request.text,
            "length": len(request.text),
            "status": "success"
        }
    except Exception as e:
        logger.error("Echo failed: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e))


def main() -> None:
    """Run the MCP server."""
    logger.info("Starting MCP echo server")
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8766)
