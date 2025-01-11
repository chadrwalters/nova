import numpy as np
import pytest
from unittest.mock import patch

from nova.rag.ephemeral import EphemeralDataManager


@patch('time.time')
def test_ephemeral_data_basic(mock_time):
    # Mock time to start at 0
    current_time = 0
    mock_time.return_value = current_time
    
    # Create manager with 10s TTL
    manager = EphemeralDataManager(ttl=10)
    
    # Add test data
    data_id = manager.add_data(
        content="Test content",
        metadata={"key": "value"}
    )
    
    # Verify data exists
    data = manager.get_data(data_id)
    assert data is not None
    assert data.content == "Test content"
    assert "key" in data.metadata and data.metadata["key"] == "value"
    assert "id" in data.metadata and data.metadata["id"] == data_id
    assert data.expiration == 10  # current_time + ttl
    
    # Advance time but not past expiration
    current_time += 5
    mock_time.return_value = current_time
    
    # Verify data still exists
    data = manager.get_data(data_id)
    assert data is not None
    
    # Advance time past expiration
    current_time += 6
    mock_time.return_value = current_time
    
    # Verify data is expired
    data = manager.get_data(data_id)
    assert data is None


@patch('time.time')
def test_ephemeral_data_with_embedding(mock_time):
    # Mock time
    mock_time.return_value = 0
    
    # Create manager with small dimension for stability
    manager = EphemeralDataManager(embedding_dim=4)
    
    # Add test data with embedding
    embedding = np.array([1, 0, 0, 0], dtype=np.float32)
    data_id = manager.add_data(
        content="Test content",
        embedding=embedding
    )
    
    # Verify data was added to vector store
    results = manager.store.search(embedding, k=1)
    assert len(results) == 1
    assert results[0].chunk.content == "Test content"
    assert results[0].chunk.metadata["id"] == data_id


@patch('time.time')
def test_ephemeral_data_ttl_extension(mock_time):
    # Mock time to start at 0
    current_time = 0
    mock_time.return_value = current_time
    
    # Create manager with 10s TTL and small dimension
    manager = EphemeralDataManager(ttl=10, embedding_dim=4)
    
    # Add test data with embedding
    embedding = np.array([1, 0, 0, 0], dtype=np.float32)
    data_id = manager.add_data(
        content="Test content",
        embedding=embedding
    )
    
    # Advance time close to expiration
    current_time += 9
    mock_time.return_value = current_time
    
    # Extend TTL by 10s
    success = manager.extend_ttl(data_id, 10)
    assert success
    
    # Verify new expiration
    data = manager.get_data(data_id)
    assert data is not None
    assert data.expiration == 19  # current_time + extension
    
    # Advance time past original expiration but before extension
    current_time += 2
    mock_time.return_value = current_time
    
    # Verify data still exists
    data = manager.get_data(data_id)
    assert data is not None
    
    # Verify search still works
    results = manager.store.search(embedding, k=1)
    assert len(results) == 1
    assert results[0].chunk.content == "Test content"


@patch('time.time')
def test_ephemeral_data_cleanup(mock_time):
    # Mock time to start at 0
    current_time = 0
    mock_time.return_value = current_time
    
    # Create manager with small dimension
    manager = EphemeralDataManager(embedding_dim=4)
    
    # Add test data with different TTLs and embeddings
    embedding1 = np.array([1, 0, 0, 0], dtype=np.float32)
    embedding2 = np.array([0, 1, 0, 0], dtype=np.float32)
    
    id1 = manager.add_data("Content 1", ttl=5, embedding=embedding1)
    id2 = manager.add_data("Content 2", ttl=10, embedding=embedding2)
    
    # Advance time past first expiration
    current_time += 7
    mock_time.return_value = current_time
    
    # Run cleanup
    manager.cleanup()
    
    # Verify first data is cleaned up but second remains
    assert manager.get_data(id1) is None
    assert manager.get_data(id2) is not None
    
    # Verify search only finds second embedding
    results = manager.store.search(embedding2, k=2)
    assert len(results) == 1
    assert results[0].chunk.content == "Content 2" 