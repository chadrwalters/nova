"""Vector store monitoring integration."""

from typing import Protocol, List, Optional
import numpy as np
from dataclasses import dataclass
import logging
import faiss

from .metrics import (
    VECTOR_SEARCH_LATENCY,
    VECTOR_STORE_SIZE,
    VECTOR_STORE_MEMORY,
    VECTOR_STORE_VECTORS,
    update_vector_store_metrics,
    track_time,
    init_metrics
)
from .alerts import AlertManager
from .memory import MemoryMonitor

logger = logging.getLogger(__name__)

# Initialize metrics
init_metrics()

@dataclass
class VectorStoreMetrics:
    """Vector store performance metrics."""
    total_vectors: int
    dimension: int
    memory_usage: int  # bytes
    index_type: str
    gpu_device: Optional[int] = None


class MonitoredVectorStore(Protocol):
    """Protocol for vector stores that support monitoring."""
    
    def get_metrics(self) -> VectorStoreMetrics:
        """Get current vector store metrics."""
        ...

    def search(self, query_vector: np.ndarray, k: int) -> List[tuple[int, float]]:
        """Search for similar vectors."""
        ...


class VectorStoreMonitor:
    """Monitor for vector store operations."""

    def __init__(self, store: MonitoredVectorStore, alert_manager: AlertManager, memory_monitor: Optional[MemoryMonitor] = None):
        self.store = store
        self.alert_manager = alert_manager
        self.memory_monitor = memory_monitor or MemoryMonitor()
        self.logger = logger

    def update_metrics(self) -> None:
        """Update vector store metrics."""
        metrics = None
        try:
            metrics = self.store.get_metrics()
            
            # Update Prometheus metrics
            update_vector_store_metrics(
                total_vectors=metrics.total_vectors,
                memory_usage=metrics.memory_usage,
                index_size=self.memory_monitor.estimate_index_size(
                    num_vectors=metrics.total_vectors,
                    dimension=metrics.dimension,
                    index_type=metrics.index_type.lower()
                )
            )
            
            # Check memory pressure
            if self.memory_monitor.check_memory_pressure():
                self.logger.warning("Memory pressure detected in vector store")
                self.alert_manager.trigger_alert(
                    "memory_pressure",
                    f"Memory pressure detected: {metrics.index_type} index using {metrics.memory_usage} bytes"
                )
            
        except Exception as e:
            self.logger.error(f"Failed to update vector store metrics: {e}")
            self.alert_manager.trigger_alert(
                "metric_update_error",
                f"Failed to update vector store metrics: {e}"
            )
        
        finally:
            # Always check alerts, even if there was an error
            if metrics:
                self.alert_manager.check_vector_store_size(metrics.total_vectors)
            else:
                # If we couldn't get metrics, check with 0 to trigger potential alerts
                self.alert_manager.check_vector_store_size(0)

    @track_time(VECTOR_SEARCH_LATENCY.labels(store_type='test'))
    def search(self, query_vector: np.ndarray, k: int) -> List[tuple[int, float]]:
        """Monitored vector search."""
        return self.store.search(query_vector, k)

    def get_memory_summary(self) -> dict:
        """Get memory usage summary."""
        return self.memory_monitor.get_memory_summary()


class MonitoredFAISS:
    """FAISS vector store with monitoring support."""

    def __init__(self, index, dimension: int, gpu_device: Optional[int] = None, memory_monitor: Optional[MemoryMonitor] = None):
        self.index = index
        self.dimension = dimension
        self.memory_monitor = memory_monitor or MemoryMonitor()
        
        # Auto-detect GPU if not specified
        if gpu_device is None and faiss.get_num_gpus() > 0:
            self.gpu_device = 0
        else:
            self.gpu_device = gpu_device

    def get_metrics(self) -> VectorStoreMetrics:
        """Get FAISS index metrics."""
        memory_usage = self._estimate_memory_usage()
        
        return VectorStoreMetrics(
            total_vectors=self.index.ntotal,
            dimension=self.dimension,
            memory_usage=memory_usage,
            index_type=self.index.__class__.__name__,
            gpu_device=self.gpu_device
        )

    def search(self, query_vector: np.ndarray, k: int) -> List[tuple[int, float]]:
        """Search FAISS index."""
        if len(query_vector.shape) == 1:
            query_vector = query_vector.reshape(1, -1)
        query_vector = query_vector.astype('float32')
        
        distances, indices = self.index.search(query_vector, k)
        return list(zip(indices[0], distances[0]))

    def _estimate_memory_usage(self) -> int:
        """Estimate memory usage of FAISS index in bytes."""
        return self.memory_monitor.estimate_index_size(
            num_vectors=self.index.ntotal,
            dimension=self.dimension,
            index_type=self.index.__class__.__name__.lower()
        ) 