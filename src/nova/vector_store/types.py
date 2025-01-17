"""Type definitions for vector store."""

from dataclasses import dataclass


@dataclass
class VectorStoreStats:
    """Statistics for the vector store."""

    collection_name: str
    num_embeddings: int
    metadata: dict[str, list[str]] | None = None
