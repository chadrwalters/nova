"""Nova processing module."""

import time
from pathlib import Path
from typing import List, Optional, Dict

import numpy as np
from sentence_transformers import SentenceTransformer
import faiss

from nova.types import Document, Chunk, SearchResult
from nova.processing.chunking import ChunkingEngine  # Re-export advanced implementation
from nova.processing.vector_store import VectorStore, EphemeralVectorStore  # Re-export advanced implementations


class EmbeddingService:
    """Handles embedding generation."""
    
    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        """Initialize embedding model."""
        self.model = SentenceTransformer(model_name)
    
    async def embed_chunks(self, chunks: List[Chunk]) -> np.ndarray:
        """Generate embeddings for chunks."""
        texts = [chunk.content for chunk in chunks]
        embeddings = self.model.encode(texts)
        return embeddings
