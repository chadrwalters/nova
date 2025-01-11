"""Unified ephemeral data management."""

import time
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
from pathlib import Path

import numpy as np
import faiss

from nova.types import Chunk, SearchResult
from nova.monitoring.metrics import (
    VECTOR_SEARCH_LATENCY,
    VECTOR_STORE_MEMORY,
    VECTOR_STORE_SIZE,
    VECTOR_STORE_VECTORS
)
from nova.monitoring.alerts import AlertManager
from nova.monitoring.memory import MemoryMonitor

logger = logging.getLogger(__name__)


@dataclass
class EphemeralData:
    """Container for ephemeral data with TTL."""
    content: str
    metadata: dict
    expiration: float
    embedding: Optional[np.ndarray] = None


class EphemeralManager:
    """Unified manager for ephemeral data with TTL and vector search."""
    
    def __init__(
        self,
        embedding_dim: int = 384,
        default_ttl: int = 300,
        cleanup_interval: int = 60,
        n_lists: Optional[int] = None,
        n_probe: Optional[int] = None,
        use_gpu: bool = True,
        alert_manager: Optional[AlertManager] = None,
        memory_monitor: Optional[MemoryMonitor] = None
    ):
        """Initialize ephemeral manager.
        
        Args:
            embedding_dim: Dimension of embeddings
            default_ttl: Default time-to-live in seconds
            cleanup_interval: How often to check for expired data
            n_lists: Number of IVF lists (if None, uses flat index)
            n_probe: Number of lists to probe (if None, uses n_lists/4)
            use_gpu: Whether to use GPU acceleration if available
            alert_manager: Optional alert manager for monitoring
            memory_monitor: Optional memory monitor for tracking usage
        """
        self.embedding_dim = embedding_dim
        self.default_ttl = default_ttl
        self.cleanup_interval = cleanup_interval
        self.n_lists = n_lists
        self.n_probe = n_probe or (n_lists // 4 if n_lists else None)
        self.use_gpu = use_gpu and faiss.get_num_gpus() > 0
        self.alert_manager = alert_manager
        self.memory_monitor = memory_monitor or MemoryMonitor()
        
        # Initialize FAISS index
        if n_lists is None:
            self.index = faiss.IndexFlatL2(embedding_dim)
        else:
            quantizer = faiss.IndexFlatL2(embedding_dim)
            self.index = faiss.IndexIVFFlat(quantizer, embedding_dim, n_lists)
            self.index.nprobe = self.n_probe
        
        # Move to GPU if available
        self.gpu_resources = None
        if self.use_gpu:
            try:
                self.gpu_resources = faiss.StandardGpuResources()
                self.index = faiss.index_cpu_to_gpu(self.gpu_resources, 0, self.index)
                logger.info("Successfully initialized GPU resources")
            except Exception as e:
                logger.warning(f"Failed to initialize GPU, falling back to CPU: {e}")
                self.use_gpu = False
        
        # Initialize storage
        self.data: Dict[str, EphemeralData] = {}
        self._id_to_idx: Dict[str, int] = {}  # Maps string IDs to FAISS indices
        self.next_id = 0
        self.last_cleanup = time.time()
        
        # Initialize metrics
        store_type = "faiss_gpu" if self.use_gpu else "faiss_cpu"
        self._search_latency = VECTOR_SEARCH_LATENCY.labels(store_type=store_type)
        self._memory_gauge = VECTOR_STORE_MEMORY.labels(store_type=store_type)
        self._size_gauge = VECTOR_STORE_SIZE.labels(store_type=store_type)
        self._vectors_gauge = VECTOR_STORE_VECTORS.labels(store_type=store_type)
        
        self._update_metrics()
    
    def add_data(
        self,
        content: str,
        metadata: Optional[dict] = None,
        ttl: Optional[int] = None,
        embedding: Optional[np.ndarray] = None
    ) -> str:
        """Add ephemeral data with optional embedding.
        
        Args:
            content: The content to store
            metadata: Optional metadata dictionary
            ttl: Optional TTL override (uses default if not specified)
            embedding: Optional embedding vector
            
        Returns:
            String ID of the stored data
        """
        # Generate ID and set expiration
        data_id = f"ephemeral_{int(time.time())}_{len(self.data)}"
        expiration = time.time() + (ttl or self.default_ttl)
        
        # Create metadata with ID
        metadata = metadata or {}
        metadata["id"] = data_id
        
        # Store data
        self.data[data_id] = EphemeralData(
            content=content,
            metadata=metadata,
            expiration=expiration,
            embedding=embedding
        )
        
        # Add to vector store if embedding provided
        if embedding is not None:
            # Ensure embedding is float32 and reshaped correctly
            if len(embedding.shape) == 1:
                embedding = embedding.reshape(1, -1)
            embedding = embedding.astype(np.float32)
            
            # Add to index
            try:
                self.index.add(embedding)
                self._id_to_idx[data_id] = self.next_id
                self.next_id += 1
            except Exception as e:
                logger.error(f"Failed to add embedding to index: {e}")
                # Remove data if index update fails
                del self.data[data_id]
                return None
        
        self._maybe_cleanup()
        self._update_metrics()
        return data_id
    
    def get_data(self, data_id: str) -> Optional[EphemeralData]:
        """Get ephemeral data if not expired."""
        if data_id not in self.data:
            return None
        
        data = self.data[data_id]
        if time.time() > data.expiration:
            self._cleanup_expired({data_id})
            return None
        
        return data
    
    def extend_ttl(self, data_id: str, extension: int) -> bool:
        """Extend TTL for data if it exists and not expired."""
        data = self.get_data(data_id)
        if data is None:
            return False
        
        data.expiration = time.time() + extension
        return True
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[SearchResult]:
        """Search for similar vectors among non-expired data."""
        self._maybe_cleanup()
        
        if self.next_id == 0:
            return []
        
        if len(query_embedding.shape) == 1:
            query_embedding = query_embedding.reshape(1, -1)
        query_embedding = query_embedding.astype(np.float32)
        
        with self._search_latency.time():
            try:
                distances, indices = self.index.search(query_embedding, k)
            except Exception as e:
                logger.error(f"Search failed: {e}")
                return []
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx < 0 or idx >= self.next_id:
                    continue
                
                # Find data_id for this index
                data_id = next(
                    (id for id, index in self._id_to_idx.items() if index == idx),
                    None
                )
                if data_id is None or data_id not in self.data:
                    continue
                
                data = self.data[data_id]
                results.append(SearchResult(
                    chunk=Chunk(
                        content=data.content,
                        metadata=data.metadata,
                        embedding=data.embedding,
                        is_ephemeral=True,
                        expiration=data.expiration
                    ),
                    score=float(distances[0][i]),
                    metadata=data.metadata.copy()
                ))
            
            return results
    
    def _maybe_cleanup(self):
        """Run cleanup if enough time has passed."""
        now = time.time()
        if now - self.last_cleanup >= self.cleanup_interval:
            self._cleanup_expired()
            self.last_cleanup = now
    
    def _cleanup_expired(self, specific_ids: Optional[Set[str]] = None):
        """Remove expired data.
        
        Args:
            specific_ids: Optional set of IDs to check and remove if expired
        """
        now = time.time()
        
        # Find expired IDs
        if specific_ids is not None:
            expired = {
                id for id in specific_ids
                if id in self.data and self.data[id].expiration <= now
            }
        else:
            expired = {
                id for id, data in self.data.items()
                if data.expiration <= now
            }
        
        if not expired:
            return
        
        # Get indices to remove
        idx_to_remove = {
            self._id_to_idx[id]
            for id in expired
            if id in self._id_to_idx
        }
        
        # Remove from storage
        for id in expired:
            del self.data[id]
            if id in self._id_to_idx:
                del self._id_to_idx[id]
        
        # Rebuild index if needed
        if idx_to_remove:
            remaining_indices = []
            new_id_to_idx = {}
            next_id = 0
            
            # Collect remaining vectors
            for id, idx in self._id_to_idx.items():
                if idx not in idx_to_remove:
                    remaining_indices.append(idx)
                    new_id_to_idx[id] = next_id
                    next_id += 1
            
            if not remaining_indices:
                # All vectors removed, reset index
                if isinstance(self.index, faiss.IndexIVF):
                    quantizer = faiss.IndexFlatL2(self.embedding_dim)
                    self.index = faiss.IndexIVFFlat(
                        quantizer,
                        self.embedding_dim,
                        self.n_lists
                    )
                    self.index.nprobe = self.n_probe
                else:
                    self.index = faiss.IndexFlatL2(self.embedding_dim)
                
                if self.use_gpu:
                    try:
                        self.index = faiss.index_cpu_to_gpu(
                            self.gpu_resources,
                            0,
                            self.index
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to move rebuilt index to GPU: {e}"
                        )
            else:
                # Extract remaining vectors
                remaining_indices = np.array(remaining_indices)
                remaining_vectors = self.index.reconstruct_batch(remaining_indices)
                
                # Create new index
                if isinstance(self.index, faiss.IndexIVF):
                    quantizer = faiss.IndexFlatL2(self.embedding_dim)
                    new_index = faiss.IndexIVFFlat(
                        quantizer,
                        self.embedding_dim,
                        self.n_lists
                    )
                    new_index.train(remaining_vectors)
                    new_index.add(remaining_vectors)
                    new_index.nprobe = self.n_probe
                else:
                    new_index = faiss.IndexFlatL2(self.embedding_dim)
                    new_index.add(remaining_vectors)
                
                if self.use_gpu:
                    try:
                        new_index = faiss.index_cpu_to_gpu(
                            self.gpu_resources,
                            0,
                            new_index
                        )
                    except Exception as e:
                        logger.warning(
                            f"Failed to move rebuilt index to GPU: {e}"
                        )
                
                self.index = new_index
            
            self._id_to_idx = new_id_to_idx
            self.next_id = next_id
        
        self._update_metrics()
        
        # Alert if significant memory change
        if self.alert_manager and self.memory_monitor.check_memory_pressure():
            self.alert_manager.trigger_alert(
                "memory_pressure",
                "Memory pressure detected after ephemeral data cleanup"
            )
    
    def _update_metrics(self):
        """Update monitoring metrics."""
        try:
            # Calculate memory usage
            bytes_per_vector = self.embedding_dim * 4  # float32
            vector_memory = self.next_id * bytes_per_vector
            
            # Update metrics
            self._memory_gauge.set(vector_memory)
            self._size_gauge.set(vector_memory)
            self._vectors_gauge.set(self.next_id)
            
            # Log significant changes
            if self.next_id > 1000:
                logger.info(
                    f"Large ephemeral store: {self.next_id} vectors, "
                    f"{vector_memory / 1024 / 1024:.2f}MB"
                )
        except Exception as e:
            logger.error(f"Failed to update ephemeral metrics: {e}") 