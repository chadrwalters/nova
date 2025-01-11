import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Set

import numpy as np

from nova.processing.types import Chunk
from nova.processing.vector_store import EphemeralVectorStore


@dataclass
class EphemeralData:
    """Container for ephemeral data with TTL."""
    content: str
    metadata: dict
    expiration: float
    embedding: Optional[np.ndarray] = None


class EphemeralDataManager:
    """Manages ephemeral data with TTL."""
    
    def __init__(self, ttl: int = 300, embedding_dim: int = 384):
        """Initialize manager with default TTL in seconds."""
        self.ttl = ttl
        self.store = EphemeralVectorStore(embedding_dim=embedding_dim)
        self._data: Dict[str, EphemeralData] = {}
        
    def add_data(
        self,
        content: str,
        metadata: Optional[dict] = None,
        ttl: Optional[int] = None,
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """Add ephemeral data with optional TTL override."""
        # Generate ID and set expiration
        data_id = f"ephemeral_{int(time.time())}_{len(self._data)}"
        expiration = time.time() + (ttl or self.ttl)
        
        # Create metadata with ID
        metadata = metadata or {}
        metadata["id"] = data_id
        
        # Store data
        self._data[data_id] = EphemeralData(
            content=content,
            metadata=metadata,
            expiration=expiration,
            embedding=embedding
        )
        
        # Add to vector store if embedding provided
        if embedding is not None:
            chunk = Chunk(
                content=content,
                source="ephemeral",
                embedding=embedding,
                metadata=metadata,
                is_ephemeral=True,
                expiration=expiration
            )
            # Ensure embedding is float32 and reshaped correctly
            embeddings = np.array([embedding], dtype=np.float32)
            self.store.add_chunks([chunk], embeddings)
            
        return data_id
        
    def get_data(self, data_id: str) -> Optional[EphemeralData]:
        """Get ephemeral data if not expired."""
        if data_id not in self._data:
            return None
            
        data = self._data[data_id]
        if time.time() > data.expiration:
            self._cleanup_expired({data_id})
            return None
            
        return data
        
    def extend_ttl(self, data_id: str, extension: int) -> bool:
        """Extend TTL for data if it exists and not expired."""
        data = self.get_data(data_id)
        if data is None:
            return False
            
        # Update expiration in both data and vector store
        new_expiration = time.time() + extension
        data.expiration = new_expiration
        
        if data.embedding is not None:
            chunk = Chunk(
                content=data.content,
                source="ephemeral",
                embedding=data.embedding,
                metadata=data.metadata,
                is_ephemeral=True,
                expiration=new_expiration
            )
            embeddings = np.array([data.embedding], dtype=np.float32)
            self.store.add_chunks([chunk], embeddings)
            
        return True
        
    def cleanup(self) -> None:
        """Clean up all expired data."""
        now = time.time()
        expired = {
            data_id
            for data_id, data in self._data.items()
            if data.expiration <= now
        }
        self._cleanup_expired(expired)
        
    def _cleanup_expired(self, expired: Set[str]) -> None:
        """Clean up specified expired data."""
        # Remove from vector store
        self.store.remove_chunks(expired)
        
        # Remove from data dict
        for data_id in expired:
            if data_id in self._data:
                del self._data[data_id] 