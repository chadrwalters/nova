"""Nova MCP server."""

import logging
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

from nova.vector_store.chunking import Chunk
from nova.vector_store.stats import VectorStoreStats
from nova.vector_store.store import VectorStore

# Initialize logging
logger = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI(title="Nova MCP", description="Nova Master Control Program", version="0.1.0")

# Initialize components
vector_store = VectorStore(base_path=str(Path(".nova/vectors")))
vector_stats = VectorStoreStats(vector_dir=str(Path(".nova/vectors")))


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

    text: str = Field(description="The text content of the chunk")
    source: str = Field(default="", description="Source file path")
    heading_text: str = Field(default="", description="Heading text")
    heading_level: int = Field(default=1, description="Heading level")
    tags: str | list[str] = Field(default_factory=list, description="Tags as string or list")
    attachments: str | list[str | dict[str, Any]] = Field(
        default_factory=list, description="Attachments as string or list"
    )


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
        )
        chunk._tags = (
            request.tags
            if isinstance(request.tags, list)
            else [t.strip() for t in request.tags.split(",")]
        )

        # Convert attachments to proper format
        if isinstance(request.attachments, str):
            chunk._attachments = [
                {"type": "unknown", "path": a.strip()} for a in request.attachments.split(",")
            ]
        else:
            chunk._attachments = [
                att if isinstance(att, dict) else {"type": "unknown", "path": str(att)}
                for att in request.attachments
            ]

        # Add to store
        metadata = chunk.to_metadata()
        vector_store.add_chunk(chunk, metadata)

        return {"status": "success"}

    except Exception as e:
        logger.error(f"Error adding chunk: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/stats")
async def get_stats() -> dict[str, Any]:
    """Get vector store statistics."""
    try:
        return vector_stats.get_stats()
    except Exception as e:
        logger.error(f"Error getting stats: {e}")
        raise HTTPException(status_code=500, detail=str(e))
