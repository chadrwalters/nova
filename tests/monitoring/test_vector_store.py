"""Tests for vector store monitoring."""

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock, ANY
from nova.monitoring.vector_store import (
    VectorStoreMetrics,
    VectorStoreMonitor,
    MonitoredFAISS
)
from nova.monitoring.memory import MemoryMonitor
from nova.monitoring.metrics import (
    VECTOR_SEARCH_LATENCY,
    VECTOR_STORE_MEMORY,
    VECTOR_STORE_SIZE,
    VECTOR_STORE_VECTORS
)

@pytest.fixture(autouse=True)
def setup_metrics():
    """Setup metrics for testing."""
    # Initialize metrics with labels
    VECTOR_SEARCH_LATENCY.labels(store_type='test')
    VECTOR_STORE_MEMORY.labels(store_type='test')
    VECTOR_STORE_SIZE.labels(store_type='test')
    VECTOR_STORE_VECTORS.labels(store_type='test')

@pytest.fixture
def mock_memory_monitor():
    """Create a mock memory monitor."""
    mock = Mock(spec=MemoryMonitor)
    mock.check_memory_pressure.return_value = False
    mock.estimate_index_size.return_value = 1024 * 1024  # 1MB
    mock.get_memory_summary.return_value = {
        'system': {'total': 1024**3, 'used': 512**3},
        'gpu': [],
        'indices': {'test_index': 1024 * 1024}
    }
    return mock

@pytest.fixture
def mock_faiss_index():
    """Create a mock FAISS index."""
    mock = Mock()
    mock.ntotal = 1000
    mock.__class__.__name__ = 'IndexFlatL2'
    mock.d = 128  # Add dimension attribute
    mock.search.return_value = (
        np.array([[0.1, 0.2]], dtype=np.float32),  # distances
        np.array([[1, 2]], dtype=np.int64)         # indices
    )
    return mock

@pytest.fixture
def mock_alert_manager():
    """Create a mock alert manager."""
    mock = Mock()
    mock.check_vector_store_size = Mock()
    mock.trigger_alert = Mock()
    return mock

@pytest.fixture
def monitored_faiss(mock_faiss_index, mock_memory_monitor):
    """Create a monitored FAISS instance."""
    with patch('nova.monitoring.vector_store.faiss') as mock_faiss:
        mock_faiss.get_num_gpus = Mock(return_value=0)
        instance = MonitoredFAISS(mock_faiss_index, dimension=128, memory_monitor=mock_memory_monitor)
        return instance

@pytest.fixture
def vector_store_monitor(monitored_faiss, mock_alert_manager, mock_memory_monitor):
    """Create a vector store monitor instance."""
    return VectorStoreMonitor(monitored_faiss, mock_alert_manager, memory_monitor=mock_memory_monitor)

def test_vector_store_metrics():
    """Test VectorStoreMetrics dataclass."""
    metrics = VectorStoreMetrics(
        total_vectors=1000,
        dimension=128,
        memory_usage=1024 * 1024,
        index_type='IndexFlatL2',
        gpu_device=None
    )
    
    assert metrics.total_vectors == 1000
    assert metrics.dimension == 128
    assert metrics.memory_usage == 1024 * 1024
    assert metrics.index_type == 'IndexFlatL2'
    assert metrics.gpu_device is None

def test_monitored_faiss_init(monitored_faiss, mock_memory_monitor):
    """Test MonitoredFAISS initialization."""
    assert monitored_faiss.dimension == 128
    assert monitored_faiss.gpu_device is None
    assert monitored_faiss.memory_monitor == mock_memory_monitor

def test_monitored_faiss_get_metrics(monitored_faiss, mock_memory_monitor):
    """Test getting metrics from MonitoredFAISS."""
    metrics = monitored_faiss.get_metrics()
    
    assert isinstance(metrics, VectorStoreMetrics)
    assert metrics.total_vectors == 1000
    assert metrics.dimension == 128
    assert metrics.index_type == 'IndexFlatL2'
    assert metrics.memory_usage == mock_memory_monitor.estimate_index_size.return_value

@patch('time.time', return_value=123.0)
def test_monitored_faiss_search(mock_time, monitored_faiss):
    """Test vector search with monitoring."""
    query = np.random.randn(128).astype('float32')
    results = monitored_faiss.search(query, k=2)
    
    assert len(results) == 2
    monitored_faiss.index.search.assert_called_once()
    np.testing.assert_array_equal(
        monitored_faiss.index.search.call_args[0][0],
        query.reshape(1, -1)
    )

def test_vector_store_monitor_update_metrics(vector_store_monitor, mock_alert_manager, mock_memory_monitor):
    """Test updating vector store metrics."""
    vector_store_monitor.update_metrics()
    mock_alert_manager.check_vector_store_size.assert_called_once()

def test_vector_store_monitor_memory_pressure(vector_store_monitor, mock_alert_manager, mock_memory_monitor):
    """Test memory pressure monitoring."""
    mock_memory_monitor.check_memory_pressure.return_value = True
    vector_store_monitor.update_metrics()
    mock_alert_manager.trigger_alert.assert_called_once()

@patch('time.time', return_value=123.0)
def test_vector_store_monitor_search(mock_time, vector_store_monitor):
    """Test monitored vector search."""
    query = np.random.randn(128).astype('float32')
    results = vector_store_monitor.search(query, k=2)
    assert len(results) == 2

def test_vector_store_monitor_get_memory_summary(vector_store_monitor, mock_memory_monitor):
    """Test getting memory summary."""
    summary = vector_store_monitor.get_memory_summary()
    assert summary == mock_memory_monitor.get_memory_summary.return_value

@patch('nova.monitoring.vector_store.faiss')
def test_monitored_faiss_gpu_support(mock_faiss, mock_faiss_index, mock_memory_monitor):
    """Test GPU support detection."""
    mock_faiss.get_num_gpus.return_value = 1
    monitored = MonitoredFAISS(mock_faiss_index, dimension=128, memory_monitor=mock_memory_monitor)
    assert monitored.gpu_device == 0

def test_vector_store_monitor_error_handling(vector_store_monitor, mock_alert_manager, mock_memory_monitor):
    """Test error handling in monitor."""
    mock_memory_monitor.check_memory_pressure.side_effect = Exception("Test error")
    vector_store_monitor.update_metrics()  # Should not raise
    mock_alert_manager.trigger_alert.assert_called_once() 