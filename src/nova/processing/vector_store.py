"""Vector store using FAISS with optimized configuration."""

import time
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple
import logging
import json
from datetime import datetime

import faiss
import numpy as np

from nova.types import Chunk, SearchResult
from nova.monitoring.metrics import (
    VECTOR_SEARCH_LATENCY,
    VECTOR_STORE_MEMORY,
    VECTOR_STORE_SIZE,
    VECTOR_STORE_VECTORS
)

logger = logging.getLogger(__name__)

class VectorStore:
    """Optimized vector store using FAISS index."""
    
    def __init__(
        self,
        embedding_dim: int = 384,
        n_lists: Optional[int] = None,
        n_probe: Optional[int] = None,
        use_gpu: bool = False
    ):
        """Initialize vector store.
        
        Args:
            embedding_dim: Dimension of embeddings
            n_lists: Number of IVF lists (if None, uses flat index)
            n_probe: Number of lists to probe (if None, uses n_lists/4)
            use_gpu: Whether to use GPU acceleration if available
        """
        self.embedding_dim = embedding_dim
        self.n_lists = n_lists
        self.n_probe = n_probe or (n_lists // 4 if n_lists else None)
        self.use_gpu = use_gpu and faiss.get_num_gpus() > 0
        self.gpu_resources = None
        
        try:
            if self.use_gpu:
                self.gpu_resources = faiss.StandardGpuResources()
                logger.info("Successfully initialized GPU resources")
        except Exception as e:
            logger.warning(f"Failed to initialize GPU, falling back to CPU: {e}")
            self.use_gpu = False
        
        # Create appropriate index
        if n_lists is None:
            self.index = faiss.IndexFlatL2(embedding_dim)
        else:
            # Create IVF index with training data
            quantizer = faiss.IndexFlatL2(embedding_dim)
            self.index = faiss.IndexIVFFlat(quantizer, embedding_dim, n_lists)
            self.index.nprobe = self.n_probe
        
        if self.use_gpu:
            try:
                self.index = faiss.index_cpu_to_gpu(self.gpu_resources, 0, self.index)
            except Exception as e:
                logger.warning(f"Failed to move index to GPU, falling back to CPU: {e}")
                self.use_gpu = False
        
        self.chunks: Dict[int, Chunk] = {}
        self.next_id = 0
        
        # Initialize metrics with labels
        store_type = "faiss_gpu" if self.use_gpu else "faiss_cpu"
        self._search_latency = VECTOR_SEARCH_LATENCY.labels(store_type=store_type)
        self._memory_gauge = VECTOR_STORE_MEMORY.labels(store_type=store_type)
        self._size_gauge = VECTOR_STORE_SIZE.labels(store_type=store_type)
        self._vectors_gauge = VECTOR_STORE_VECTORS.labels(store_type=store_type)
        
        # Initialize metrics with zero
        self._memory_gauge.set(0)
        self._size_gauge.set(0)
        self._vectors_gauge.set(0)
    
    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray):
        """Add chunks with optimized batching."""
        if len(chunks) != embeddings.shape[0]:
            raise ValueError("Number of chunks must match number of embeddings")
            
        embeddings = embeddings.astype(np.float32)
        
        # Train index if needed
        if isinstance(self.index, faiss.IndexIVF) and not self.index.is_trained:
            logger.info("Training IVF index...")
            self.index.train(embeddings)
        
        # Add to index in small batches for stability
        batch_size = 1000
        for i in range(0, len(embeddings), batch_size):
            batch_end = min(i + batch_size, len(embeddings))
            batch_embeddings = embeddings[i:batch_end]
            
            try:
                self.index.add(batch_embeddings)
            except Exception as e:
                logger.error(f"Failed to add batch to index: {e}")
                raise
            
            # Store chunks
            for j in range(i, batch_end):
                self.chunks[self.next_id + j - i] = chunks[j]
        
        self.next_id += len(chunks)
        self._update_memory_usage()
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[SearchResult]:
        """Search with optimized index."""
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
                    
                chunk = self.chunks[idx]
                results.append(SearchResult(
                    chunk=chunk,
                    score=float(distances[0][i]),
                    metadata=chunk.metadata.copy()
                ))
            
            return results
    
    def save(self, save_dir: Path) -> None:
        """Save vector store state."""
        save_dir = Path(save_dir)
        save_dir.mkdir(parents=True, exist_ok=True)
        
        # Save index
        if self.use_gpu:
            cpu_index = faiss.index_gpu_to_cpu(self.index)
            faiss.write_index(cpu_index, str(save_dir / "index.faiss"))
        else:
            faiss.write_index(self.index, str(save_dir / "index.faiss"))
        
        # Save chunks
        chunks_data = {
            str(idx): {
                "content": chunk.content,
                "metadata": chunk.metadata,
                "is_ephemeral": chunk.is_ephemeral,
                "expiration": chunk.expiration
            }
            for idx, chunk in self.chunks.items()
        }
        
        with open(save_dir / "chunks.json", "w") as f:
            json.dump(chunks_data, f)
        
        # Save config
        config = {
            "embedding_dim": self.embedding_dim,
            "n_lists": self.n_lists,
            "n_probe": self.n_probe,
            "use_gpu": self.use_gpu,
            "next_id": self.next_id
        }
        
        with open(save_dir / "config.json", "w") as f:
            json.dump(config, f)
    
    def load(self, save_dir: Path) -> None:
        """Load vector store state."""
        save_dir = Path(save_dir)
        
        # Load config
        with open(save_dir / "config.json", "r") as f:
            config = json.load(f)
        
        self.embedding_dim = config["embedding_dim"]
        self.n_lists = config["n_lists"]
        self.n_probe = config["n_probe"]
        self.next_id = config["next_id"]
        
        # Load index
        self.index = faiss.read_index(str(save_dir / "index.faiss"))
        if config["use_gpu"] and self.use_gpu:
            try:
                self.index = faiss.index_cpu_to_gpu(self.gpu_resources, 0, self.index)
            except Exception as e:
                logger.warning(f"Failed to move loaded index to GPU: {e}")
        
        # Load chunks
        with open(save_dir / "chunks.json", "r") as f:
            chunks_data = json.load(f)
        
        self.chunks = {
            int(idx): Chunk(
                content=data["content"],
                metadata=data["metadata"],
                is_ephemeral=data["is_ephemeral"],
                expiration=data["expiration"]
            )
            for idx, data in chunks_data.items()
        }
        
        self._update_memory_usage()
    
    def _update_memory_usage(self) -> int:
        """Update memory usage metrics."""
        try:
            # Estimate memory usage
            bytes_per_vector = self.embedding_dim * 4  # float32
            vector_memory = self.next_id * bytes_per_vector
            
            # Update metrics
            self._memory_gauge.set(vector_memory)
            self._size_gauge.set(vector_memory)
            self._vectors_gauge.set(self.next_id)
            
            return vector_memory
        except Exception as e:
            logger.error(f"Failed to update memory metrics: {e}")
            return 0


class EphemeralVectorStore(VectorStore):
    """Vector store for ephemeral data with automatic cleanup."""
    
    def __init__(
        self,
        embedding_dim: int = 384,
        n_lists: Optional[int] = None,
        n_probe: Optional[int] = None,
        use_gpu: bool = True,
        cleanup_interval: int = 60
    ):
        """Initialize ephemeral vector store.
        
        Args:
            embedding_dim: Dimension of embeddings
            n_lists: Number of IVF lists (if None, uses flat index)
            n_probe: Number of lists to probe (if None, uses n_lists/4)
            use_gpu: Whether to use GPU acceleration if available
            cleanup_interval: How often to check for expired data (seconds)
        """
        super().__init__(
            embedding_dim=embedding_dim,
            n_lists=n_lists,
            n_probe=n_probe,
            use_gpu=use_gpu
        )
        self.cleanup_interval = cleanup_interval
        self.last_cleanup = time.time()
        self._id_to_idx: Dict[str, int] = {}  # Map string IDs to internal indices
    
    def add_chunks(self, chunks: List[Chunk], embeddings: np.ndarray):
        """Add chunks with automatic cleanup."""
        # Map string IDs to internal indices
        for chunk in chunks:
            if chunk.metadata.get("id"):
                self._id_to_idx[chunk.metadata["id"]] = self.next_id + len(self._id_to_idx)
        
        super().add_chunks(chunks, embeddings)
        self._maybe_cleanup()
    
    def search(self, query_embedding: np.ndarray, k: int = 5) -> List[SearchResult]:
        """Search with automatic cleanup."""
        self._maybe_cleanup()
        return super().search(query_embedding, k)
    
    def _maybe_cleanup(self):
        """Run cleanup if enough time has passed."""
        now = time.time()
        if now - self.last_cleanup >= self.cleanup_interval:
            self._cleanup_expired()
            self.last_cleanup = now
    
    def _cleanup_expired(self):
        """Remove expired chunks."""
        now = time.time()
        expired = {
            chunk.metadata.get("id")
            for chunk in self.chunks.values()
            if chunk.is_ephemeral and chunk.expiration and chunk.expiration <= now
            and chunk.metadata.get("id")
        }
        if expired:
            self.remove_chunks(expired)
    
    def remove_chunks(self, chunk_ids: Set[str]):
        """Remove chunks by ID."""
        # Convert string IDs to internal indices
        idx_to_remove = {
            self._id_to_idx[chunk_id]
            for chunk_id in chunk_ids
            if chunk_id in self._id_to_idx
        }
        
        if not idx_to_remove:
            return
            
        # Create new index without removed vectors
        remaining_indices = []
        remaining_chunks = {}
        new_id_to_idx = {}
        next_id = 0
        
        for idx, chunk in self.chunks.items():
            if idx not in idx_to_remove:
                remaining_indices.append(idx)
                remaining_chunks[next_id] = chunk
                if chunk.metadata.get("id"):
                    new_id_to_idx[chunk.metadata["id"]] = next_id
                next_id += 1
        
        if not remaining_indices:
            # All chunks removed, reset index
            if isinstance(self.index, faiss.IndexIVF):
                quantizer = faiss.IndexFlatL2(self.embedding_dim)
                self.index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, self.n_lists)
                self.index.nprobe = self.n_probe
            else:
                self.index = faiss.IndexFlatL2(self.embedding_dim)
        else:
            # Extract remaining vectors
            remaining_indices = np.array(remaining_indices)
            remaining_vectors = self.index.reconstruct_batch(remaining_indices)
            
            # Create new index
            if isinstance(self.index, faiss.IndexIVF):
                quantizer = faiss.IndexFlatL2(self.embedding_dim)
                new_index = faiss.IndexIVFFlat(quantizer, self.embedding_dim, self.n_lists)
                new_index.train(remaining_vectors)
                new_index.add(remaining_vectors)
                new_index.nprobe = self.n_probe
            else:
                new_index = faiss.IndexFlatL2(self.embedding_dim)
                new_index.add(remaining_vectors)
            
            self.index = new_index
        
        self.chunks = remaining_chunks
        self._id_to_idx = new_id_to_idx
        self.next_id = next_id
        self._update_memory_usage() 