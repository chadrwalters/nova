"""Vector store module.

This module provides a vector store implementation using ChromaDB. It
handles document storage, retrieval, and semantic search functionality.
"""

import json
import logging
from pathlib import Path
from typing import Any

import chromadb
from chromadb.config import Settings
from chromadb.utils.embedding_functions import DefaultEmbeddingFunction

from nova.vector_store.chunking import Chunk

logger = logging.getLogger(__name__)

# Constants for include fields
INCLUDE_FIELDS = ["documents", "metadatas", "distances"]


def _convert_metadata_value(value: Any) -> str | int | float | bool:
    """Convert metadata value to a type supported by ChromaDB."""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


class VectorStore:
    """Vector store class."""

    COLLECTION_NAME = "nova"

    def __init__(self, base_path: str, use_memory: bool = False) -> None:
        """Initialize the vector store.

        Args:
            base_path: Base path for storing vectors
            use_memory: Whether to use in-memory storage
        """
        self.base_path = Path(base_path)

        # Initialize ChromaDB client
        if use_memory:
            settings = Settings(anonymized_telemetry=False, allow_reset=True, is_persistent=False)
        else:
            settings = Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True,
                persist_directory=str(self.base_path / "chroma"),
            )

        # Create client and collection with default embedding function
        self._client = chromadb.Client(settings)
        self._collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw_space": "cosine"},
            embedding_function=DefaultEmbeddingFunction(),
        )

    def add_chunk(self, chunk: Chunk, metadata: dict[str, Any] | None = None) -> None:
        """Add a chunk to the store.

        Args:
            chunk: The chunk to add
            metadata: Optional metadata to override chunk's default metadata
        """
        try:
            # Get metadata from chunk if not provided
            if metadata is None:
                metadata = chunk.to_metadata()

            # Convert metadata values to supported types
            processed_metadata = {k: _convert_metadata_value(v) for k, v in metadata.items()}

            # Add chunk directly to collection
            self._collection.add(
                ids=[chunk.chunk_id], documents=[chunk.text], metadatas=[processed_metadata]
            )

        except Exception as e:
            logger.error(f"Error adding chunk: {e}")
            raise

    def clear(self) -> None:
        """Clear all chunks from the store."""
        # Get all document IDs
        results = self._collection.get()
        if results["ids"]:
            # Delete all documents by ID
            self._collection.delete(ids=results["ids"])

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for chunks similar to the query.

        Args:
            query: The search query
            limit: Maximum number of results to return

        Returns:
            List of search results
        """
        # Perform search
        results = self._collection.query(
            query_texts=[query], n_results=limit, include=INCLUDE_FIELDS
        )

        # Convert to search result format
        search_results: list[dict[str, Any]] = []

        # Get result lists
        documents = results.get("documents", [])
        metadatas = results.get("metadatas", [])
        distances = results.get("distances", [])

        # Ensure we have results
        if not documents or not metadatas or not distances:
            return []

        # Get first result set
        docs = documents[0] if documents else []
        metas = metadatas[0] if metadatas else []
        dists = distances[0] if distances else []

        # Process results
        for doc, meta, dist in zip(docs, metas, dists, strict=False):
            if doc is not None and meta is not None and dist is not None:
                # Parse JSON-encoded metadata fields
                processed_meta = {}
                for k, v in meta.items():
                    if k in ["tags", "attachments"] and isinstance(v, str):
                        try:
                            processed_meta[k] = json.loads(v)
                        except json.JSONDecodeError:
                            processed_meta[k] = v
                    else:
                        processed_meta[k] = v

                search_results.append(
                    {
                        "text": str(doc),
                        "score": 1.0 - float(dist),  # Convert distance to similarity score
                        "metadata": processed_meta,
                    }
                )

        return search_results
