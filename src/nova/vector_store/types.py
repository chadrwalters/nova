"""Type definitions for vector store."""

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class VectorStoreStats:
    """Statistics for the vector store."""

    collection_name: str
    num_embeddings: int
    metadata: Optional[Dict[str, List[str]]] = None
