import time
from pathlib import Path
from typing import Dict, List, Optional, Set

import faiss
import numpy as np

from nova.processing.types import Chunk, SearchResult


class VectorStore:
    def __init__(self, embedding_dim: int = 384):
        self.embedding_dim = embedding_dim
        self.chunks: Dict[str, Chunk] = {}  # chunk_id -> Chunk
        self.embeddings: Optional[np.ndarray] = None  # Will be initialized on first add
        self.chunk_ids: List[str] = []  # Maintains order of chunks

    def add_chunks(self, chunks: List[Chunk], embeddings: Optional[np.ndarray] = None):
        if not chunks:
            return
            
        if embeddings is None:
            embeddings = np.vstack([c.embedding for c in chunks])

        # Initialize or extend embeddings array
        if self.embeddings is None:
            self.embeddings = embeddings
        else:
            self.embeddings = np.vstack([self.embeddings, embeddings])
        
        # Store chunks
        for chunk in chunks:
            self.chunks[chunk.chunk_id] = chunk
            self.chunk_ids.append(chunk.chunk_id)

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[SearchResult]:
        if self.embeddings is None or not self.chunk_ids:
            return []
            
        # Compute L2 distances
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
            
        distances = np.linalg.norm(self.embeddings - query_embedding, axis=1)
        indices = np.argsort(distances)[:k]
        
        # Convert to results
        results = []
        for idx in indices:
            chunk_id = self.chunk_ids[idx]
            chunk = self.chunks[chunk_id]
            results.append(SearchResult(
                chunk=chunk,
                score=float(distances[idx]),
                metadata=chunk.metadata.copy()
            ))
        
        return results

    def remove_chunks(self, chunk_ids: Set[str]):
        if not chunk_ids:
            return
            
        # Get indices to keep
        keep_indices = [
            i for i, chunk_id in enumerate(self.chunk_ids) 
            if chunk_id not in chunk_ids
        ]
        
        if keep_indices and self.embeddings is not None:
            self.embeddings = self.embeddings[keep_indices]
            self.chunk_ids = [self.chunk_ids[i] for i in keep_indices]
        else:
            self.embeddings = None
            self.chunk_ids = []
            
        # Update chunks dict
        for chunk_id in chunk_ids:
            if chunk_id in self.chunks:
                del self.chunks[chunk_id]


class EphemeralVectorStore(VectorStore):
    def __init__(self, embedding_dim: int = 384, **kwargs):
        super().__init__(embedding_dim)
        self.chunk_registry: Dict[str, float] = {}  # chunk_id -> expiration

    def add_chunks(self, chunks: List[Chunk], embeddings: Optional[np.ndarray] = None):
        if not all(c.is_ephemeral and c.expiration for c in chunks):
            raise ValueError("All chunks must be ephemeral with expiration time")
        
        super().add_chunks(chunks, embeddings)
        for chunk in chunks:
            if chunk.expiration is not None:
                self.chunk_registry[chunk.chunk_id] = chunk.expiration

    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[SearchResult]:
        # Clean expired chunks
        now = time.time()
        expired = {
            chunk_id 
            for chunk_id, expiration in self.chunk_registry.items()
            if expiration <= now
        }
        
        if expired:
            self.remove_chunks(expired)
            for chunk_id in expired:
                del self.chunk_registry[chunk_id]
                
        return super().search(query_embedding, k) 