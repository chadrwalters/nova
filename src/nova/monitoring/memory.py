"""Memory monitoring and tracking for Nova."""

import psutil
import torch
import numpy as np
from typing import Dict, Optional, List
from dataclasses import dataclass
from prometheus_client import Gauge
from nova.monitoring.metrics import REGISTRY, MEMORY_PRESSURE_ALERTS

@dataclass
class MemoryStats:
    total: int
    used: int
    available: int
    percent: float
    gpu_total: Optional[int] = None
    gpu_used: Optional[int] = None
    gpu_percent: Optional[float] = None

# System Memory Metrics
SYSTEM_MEMORY_TOTAL = Gauge(
    'system_memory_total_bytes',
    'Total system memory in bytes',
    registry=REGISTRY
)

SYSTEM_MEMORY_USED = Gauge(
    'system_memory_used_bytes',
    'Used system memory in bytes',
    registry=REGISTRY
)

SYSTEM_MEMORY_AVAILABLE = Gauge(
    'system_memory_available_bytes',
    'Available system memory in bytes',
    registry=REGISTRY
)

SYSTEM_MEMORY_PERCENT = Gauge(
    'system_memory_usage_percent',
    'System memory usage percentage',
    registry=REGISTRY
)

# GPU Memory Metrics
GPU_MEMORY_TOTAL = Gauge(
    'gpu_memory_total_bytes',
    'Total GPU memory in bytes',
    ['device'],
    registry=REGISTRY
)

GPU_MEMORY_USED = Gauge(
    'gpu_memory_used_bytes',
    'Used GPU memory in bytes',
    ['device'],
    registry=REGISTRY
)

GPU_MEMORY_PERCENT = Gauge(
    'gpu_memory_usage_percent',
    'GPU memory usage percentage',
    ['device'],
    registry=REGISTRY
)

# Per-Index Memory Metrics
INDEX_MEMORY_USED = Gauge(
    'index_memory_used_bytes',
    'Memory used by specific index in bytes',
    ['index_id', 'index_type'],
    registry=REGISTRY
)

class MemoryMonitor:
    def __init__(self, memory_threshold: float = 90.0, gpu_threshold: float = 85.0):
        """Initialize memory monitor.
        
        Args:
            memory_threshold: System memory usage threshold percentage for alerts
            gpu_threshold: GPU memory usage threshold percentage for alerts
        """
        self.memory_threshold = memory_threshold
        self.gpu_threshold = gpu_threshold
        self.index_memory: Dict[str, int] = {}
        
    def get_system_memory_stats(self) -> MemoryStats:
        """Get current system memory statistics."""
        mem = psutil.virtual_memory()
        stats = MemoryStats(
            total=mem.total,
            used=mem.used,
            available=mem.available,
            percent=mem.percent
        )
        
        # Update Prometheus metrics
        SYSTEM_MEMORY_TOTAL.set(stats.total)
        SYSTEM_MEMORY_USED.set(stats.used)
        SYSTEM_MEMORY_AVAILABLE.set(stats.available)
        SYSTEM_MEMORY_PERCENT.set(stats.percent)
        
        return stats
    
    def get_gpu_memory_stats(self) -> List[MemoryStats]:
        """Get GPU memory statistics if available."""
        if not torch.cuda.is_available():
            return []
            
        stats = []
        for i in range(torch.cuda.device_count()):
            gpu_stats = torch.cuda.get_device_properties(i)
            memory = torch.cuda.memory_stats(i)
            total = gpu_stats.total_memory
            used = memory.get('allocated_bytes.all.current', 0)
            percent = (used / total) * 100 if total > 0 else 0
            
            stat = MemoryStats(
                total=total,
                used=used,
                available=total - used,
                percent=percent,
                gpu_total=total,
                gpu_used=used,
                gpu_percent=percent
            )
            stats.append(stat)
            
            # Update Prometheus metrics
            GPU_MEMORY_TOTAL.labels(device=f'gpu{i}').set(total)
            GPU_MEMORY_USED.labels(device=f'gpu{i}').set(used)
            GPU_MEMORY_PERCENT.labels(device=f'gpu{i}').set(percent)
            
        return stats
    
    def track_index_memory(self, index_id: str, index_type: str, memory_bytes: int) -> None:
        """Track memory usage for a specific index.
        
        Args:
            index_id: Unique identifier for the index
            index_type: Type of index (e.g., 'faiss', 'flat', 'ivf')
            memory_bytes: Memory usage in bytes
        """
        self.index_memory[index_id] = memory_bytes
        INDEX_MEMORY_USED.labels(index_id=index_id, index_type=index_type).set(memory_bytes)
    
    def check_memory_pressure(self) -> bool:
        """Check for memory pressure conditions and trigger alerts if needed.
        
        Returns:
            bool: True if memory pressure detected, False otherwise
        """
        system_stats = self.get_system_memory_stats()
        gpu_stats = self.get_gpu_memory_stats()
        pressure_detected = False
        
        # Check system memory
        if system_stats.percent >= self.memory_threshold:
            MEMORY_PRESSURE_ALERTS.labels(severity='critical', component='system').inc()
            pressure_detected = True
            
        # Check GPU memory
        for i, gpu_stat in enumerate(gpu_stats):
            if gpu_stat.gpu_percent and gpu_stat.gpu_percent >= self.gpu_threshold:
                MEMORY_PRESSURE_ALERTS.labels(severity='critical', component=f'gpu{i}').inc()
                pressure_detected = True
                
        return pressure_detected
    
    def estimate_index_size(self, num_vectors: int, dimension: int, index_type: str = 'flat') -> int:
        """Estimate memory usage for a vector index.
        
        Args:
            num_vectors: Number of vectors in the index
            dimension: Dimensionality of vectors
            index_type: Type of index ('flat', 'ivf', etc.)
            
        Returns:
            int: Estimated memory usage in bytes
        """
        # Base memory for vector data
        vector_memory = num_vectors * dimension * np.dtype(np.float32).itemsize
        
        # Additional overhead based on index type
        if index_type == 'flat':
            overhead = 1.1  # 10% overhead for flat index
        elif index_type == 'ivf':
            overhead = 1.3  # 30% overhead for IVF index (centroids, etc.)
        else:
            overhead = 1.5  # 50% overhead for other index types
            
        return int(vector_memory * overhead)
    
    def get_memory_summary(self) -> Dict:
        """Get a summary of all memory metrics.
        
        Returns:
            Dict containing system, GPU, and index memory statistics
        """
        system_stats = self.get_system_memory_stats()
        gpu_stats = self.get_gpu_memory_stats()
        
        return {
            'system': {
                'total': system_stats.total,
                'used': system_stats.used,
                'available': system_stats.available,
                'percent': system_stats.percent
            },
            'gpu': [
                {
                    'device': i,
                    'total': stat.gpu_total,
                    'used': stat.gpu_used,
                    'percent': stat.gpu_percent
                }
                for i, stat in enumerate(gpu_stats)
            ],
            'indices': self.index_memory
        } 