"""Tests for memory monitoring module."""

import pytest
from unittest.mock import patch, MagicMock
import psutil
import torch
import numpy as np
from nova.monitoring.memory import MemoryMonitor, MemoryStats

@pytest.fixture
def memory_monitor():
    """Create a memory monitor instance for testing."""
    return MemoryMonitor(memory_threshold=90.0, gpu_threshold=85.0)

@pytest.fixture
def mock_virtual_memory():
    """Mock psutil.virtual_memory() response."""
    mock = MagicMock()
    mock.total = 16 * 1024 * 1024 * 1024  # 16GB
    mock.used = 8 * 1024 * 1024 * 1024    # 8GB
    mock.available = 8 * 1024 * 1024 * 1024  # 8GB
    mock.percent = 50.0
    return mock

@pytest.fixture
def mock_gpu_properties():
    """Mock torch.cuda.get_device_properties() response."""
    mock = MagicMock()
    mock.total_memory = 8 * 1024 * 1024 * 1024  # 8GB
    return mock

@pytest.fixture
def mock_gpu_memory_stats():
    """Mock torch.cuda.memory_stats() response."""
    return {
        'allocated_bytes.all.current': 4 * 1024 * 1024 * 1024  # 4GB
    }

def test_get_system_memory_stats(memory_monitor, mock_virtual_memory):
    """Test system memory statistics collection."""
    with patch('psutil.virtual_memory', return_value=mock_virtual_memory):
        stats = memory_monitor.get_system_memory_stats()
        
        assert isinstance(stats, MemoryStats)
        assert stats.total == mock_virtual_memory.total
        assert stats.used == mock_virtual_memory.used
        assert stats.available == mock_virtual_memory.available
        assert stats.percent == mock_virtual_memory.percent

@pytest.mark.skipif(not torch.cuda.is_available(), reason="CUDA not available")
def test_get_gpu_memory_stats_with_gpu(memory_monitor, mock_gpu_properties, mock_gpu_memory_stats):
    """Test GPU memory statistics collection when GPU is available."""
    with patch('torch.cuda.device_count', return_value=1), \
         patch('torch.cuda.get_device_properties', return_value=mock_gpu_properties), \
         patch('torch.cuda.memory_stats', return_value=mock_gpu_memory_stats):
        
        stats = memory_monitor.get_gpu_memory_stats()
        
        assert len(stats) == 1
        gpu_stats = stats[0]
        assert gpu_stats.gpu_total == mock_gpu_properties.total_memory
        assert gpu_stats.gpu_used == mock_gpu_memory_stats['allocated_bytes.all.current']
        assert gpu_stats.gpu_percent == 50.0  # 4GB used out of 8GB total

def test_get_gpu_memory_stats_no_gpu(memory_monitor):
    """Test GPU memory statistics collection when no GPU is available."""
    with patch('torch.cuda.is_available', return_value=False):
        stats = memory_monitor.get_gpu_memory_stats()
        assert len(stats) == 0

def test_track_index_memory(memory_monitor):
    """Test tracking memory usage for specific indices."""
    index_id = 'test_index'
    index_type = 'flat'
    memory_bytes = 1024 * 1024  # 1MB
    
    memory_monitor.track_index_memory(index_id, index_type, memory_bytes)
    
    assert memory_monitor.index_memory[index_id] == memory_bytes

def test_check_memory_pressure(memory_monitor):
    """Test memory pressure detection."""
    # Mock high system memory usage
    high_memory = MagicMock()
    high_memory.total = 16 * 1024 * 1024 * 1024
    high_memory.used = 15 * 1024 * 1024 * 1024
    high_memory.available = 1 * 1024 * 1024 * 1024
    high_memory.percent = 95.0
    
    with patch('psutil.virtual_memory', return_value=high_memory), \
         patch('torch.cuda.is_available', return_value=False):
        
        pressure_detected = memory_monitor.check_memory_pressure()
        assert pressure_detected is True

def test_estimate_index_size(memory_monitor):
    """Test index size estimation for different index types."""
    num_vectors = 1000
    dimension = 128
    
    # Test flat index
    flat_size = memory_monitor.estimate_index_size(num_vectors, dimension, 'flat')
    assert flat_size > num_vectors * dimension * 4  # Should be larger than raw vector size
    
    # Test IVF index
    ivf_size = memory_monitor.estimate_index_size(num_vectors, dimension, 'ivf')
    assert ivf_size > flat_size  # IVF should have more overhead

def test_get_memory_summary(memory_monitor, mock_virtual_memory):
    """Test memory summary generation."""
    with patch('psutil.virtual_memory', return_value=mock_virtual_memory), \
         patch('torch.cuda.is_available', return_value=False):
        
        # Add some index memory data
        memory_monitor.track_index_memory('index1', 'flat', 1024 * 1024)
        memory_monitor.track_index_memory('index2', 'ivf', 2 * 1024 * 1024)
        
        summary = memory_monitor.get_memory_summary()
        
        assert 'system' in summary
        assert 'gpu' in summary
        assert 'indices' in summary
        assert len(summary['indices']) == 2
        assert summary['indices']['index1'] == 1024 * 1024
        assert summary['indices']['index2'] == 2 * 1024 * 1024 