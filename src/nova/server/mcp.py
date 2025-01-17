"""Nova MCP server."""

import json
import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from nova.vector_store.chunking import Chunk
from nova.vector_store.store import VectorStore

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Nova MCP", description="Nova Master Control Program", version="0.1.0")

# Initialize components
vector_store = VectorStore(str(Path(".nova/vectors")))


# Initialize CLI commands
class SearchRequest(BaseModel):
    """Search request model."""

    query: str
    limit: int | None = 5
    tag_filter: str | None = None
    attachment_type: str | None = None


class SearchResponse(BaseModel):
    """Search response model."""

    results: list[dict[str, Any]]
    total: int
    query: str


@app.post("/search", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    """Search for documents."""
    try:
        # Perform search
        results = vector_store.search(
            query=request.query,
            limit=request.limit or 5,
            tag_filter=request.tag_filter,
            attachment_type=request.attachment_type,
        )

        # Return results
        return SearchResponse(results=results, total=len(results), query=request.query)

    except Exception as e:
        logger.error(f"Error during search: {e}")
        raise HTTPException(status_code=500, detail=str(e))


class AddChunkRequest(BaseModel):
    """Add chunk request model."""

    text: str
    source: str = ""
    heading_text: str = ""
    heading_level: int = 1
    tags: list[str] = []
    attachments: list[dict[str, Any]] = []


@app.post("/add_chunk")
async def add_chunk(request: AddChunkRequest) -> dict[str, Any]:
    """Add a chunk to the vector store."""
    try:
        # Create chunk
        chunk = Chunk(
            text=request.text,
            source=Path(request.source) if request.source else None,
            heading_text=request.heading_text,
            heading_level=request.heading_level,
            tags=request.tags,
            attachments=request.attachments,
        )

        # Add to store
        metadata = {
            "source": str(chunk.source) if chunk.source else "",
            "heading_text": chunk.heading_text,
            "heading_level": chunk.heading_level,
            "tags": ",".join(chunk.tags),
            "attachments": json.dumps(chunk.attachments),
        }
        vector_store.add_chunk(chunk, metadata)

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error adding chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats() -> dict[str, Any]:
    """Get vector store statistics."""
    try:
        return vector_store.get_stats()
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
