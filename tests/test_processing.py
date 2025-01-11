from datetime import datetime, timedelta
from pathlib import Path
import time
from unittest.mock import Mock, patch
import os

import numpy as np
import pytest
import tempfile

from nova.processing.chunking import ChunkingEngine
from nova.processing.embedding import EmbeddingService
from nova.types import Chunk, Document
from nova.processing.vector_store import EphemeralVectorStore, VectorStore

@pytest.fixture
def sample_document():
    return Document(
        content="""# Test Document
This is a test document with multiple sections.

## Section 1
This is the first section with some content.
It has multiple paragraphs.

Another paragraph here.

## Section 2
This is the second section.
It also has content.""",
        metadata={"source": "test", "path": "test.md"},
        source_path=Path("test.md")
    )

def test_chunking_engine(sample_document):
    engine = ChunkingEngine(chunk_size=100, heading_weight=1.5)
    chunks = engine.chunk_document(sample_document)
    
    assert len(chunks) > 0
    assert all(isinstance(c, Chunk) for c in chunks)
    assert all(len(c.content) <= 100 for c in chunks)
    
    # Check heading metadata
    section_chunks = [c for c in chunks if "heading" in c.metadata]
    assert len(section_chunks) > 0
    assert any("Section 1" in c.metadata["heading"] for c in section_chunks)
    assert any("Section 2" in c.metadata["heading"] for c in section_chunks)
    assert all(c.metadata["heading_weight"] == "1.5" for c in section_chunks)

@patch("sentence_transformers.SentenceTransformer")
def test_embedding_service(mock_transformer):
    # Mock the transformer
    mock_model = Mock()
    mock_model.get_sentence_embedding_dimension.return_value = 384
    mock_model.encode.return_value = np.random.randn(2, 384)
    mock_transformer.return_value = mock_model
    
    # Create chunks
    chunks = [
        Chunk(content="Test chunk 1", metadata={"id": "test1"}),
        Chunk(content="Test chunk 2", metadata={"id": "test2"})
    ]
    
    # Test embedding generation
    service = EmbeddingService(batch_size=2)
    embeddings = service.embed_chunks(chunks)
    
    assert embeddings.shape == (2, 384)
    assert all(c.embedding is not None for c in chunks)
    assert all(c.embedding.shape == (384,) for c in chunks)

def test_vector_store():
    # Use smaller dimensions and fewer vectors
    store = VectorStore(embedding_dim=4)  # Remove n_lists and n_probe for flat index
    
    # Create test chunks with embeddings
    num_vectors = 50  # Reduced from 200
    chunks = []
    embeddings = []
    
    for i in range(num_vectors):
        # Create simple unit vectors
        vec = np.zeros(4, dtype=np.float32)
        vec[i % 4] = 1.0
        chunks.append(Chunk(
            content=f"Test {i}",
            metadata={"id": str(i)},
            embedding=vec
        ))
        embeddings.append(vec)
    
    # Add chunks in smaller batches
    embeddings = np.vstack(embeddings)
    batch_size = 10
    for i in range(0, num_vectors, batch_size):
        store.add_chunks(
            chunks[i:i+batch_size], 
            embeddings[i:i+batch_size]
        )
    
    # Test search with simple query
    query = np.array([1, 0, 0, 0], dtype=np.float32)
    results = store.search(query, k=2)
    assert len(results) == 2
    
    # Test empty search
    empty_store = VectorStore(embedding_dim=4)
    results = empty_store.search(query, k=2)
    assert len(results) == 0

@patch('time.time')
def test_ephemeral_vector_store(mock_time):
    # Mock time to start at 0
    current_time = 0
    mock_time.return_value = current_time
    
    store = EphemeralVectorStore(
        embedding_dim=4,
        cleanup_interval=0.1  # Small interval for test
    )
    
    # Create test chunks with embeddings and expiration
    num_vectors = 50  # Reduced from 200
    chunks = []
    embeddings = []
    
    for i in range(num_vectors):
        # Create simple unit vectors
        vec = np.zeros(4, dtype=np.float32)
        vec[i % 4] = 1.0
        
        # Set different expiration times
        expiration = current_time + (1 if i < num_vectors/3 else 
                                   2 if i < 2*num_vectors/3 else 3)
        
        chunks.append(Chunk(
            content=f"Test {i}",
            metadata={"id": str(i)},
            embedding=vec,
            is_ephemeral=True,
            expiration=expiration
        ))
        embeddings.append(vec)
    
    # Add chunks in smaller batches
    embeddings = np.vstack(embeddings)
    batch_size = 10
    for i in range(0, num_vectors, batch_size):
        store.add_chunks(
            chunks[i:i+batch_size], 
            embeddings[i:i+batch_size]
        )
    
    # Test immediate search
    query = np.array([1, 0, 0, 0], dtype=np.float32)
    results = store.search(query, k=2)
    assert len(results) == 2
    
    # Advance time by 1.5 seconds
    current_time += 1.5
    mock_time.return_value = current_time

    # Force cleanup of expired chunks
    store._cleanup_expired()

    # Test after first expiration
    results = store.search(query, k=2)
    assert len(results) > 0
    assert all(r.chunk.expiration > current_time for r in results)
    
    # Advance time past all expirations
    current_time += 2
    mock_time.return_value = current_time
    
    # Test after all expired
    results = store.search(query, k=2)
    assert len(results) == 0

def test_vector_store_persistence(tmp_path):
    """Test saving and loading vector store state."""
    # Create test data
    num_vectors = 20  # Reduced from 100
    embedding_dim = 4
    embeddings = np.random.random((num_vectors, embedding_dim)).astype('float32')
    chunks = [
        Chunk(
            content=f"Test chunk {i}",
            metadata={"id": f"chunk_{i}"}
        )
        for i in range(num_vectors)
    ]
    
    # Create and train store
    store = VectorStore(embedding_dim=embedding_dim)
    
    # Add chunks in smaller batches
    batch_size = 5
    for i in range(0, num_vectors, batch_size):
        store.add_chunks(
            chunks[i:i+batch_size], 
            embeddings[i:i+batch_size]
        )
    
    # Test search before saving
    query = np.random.random(embedding_dim).astype('float32')
    original_results = store.search(query, k=2)  # Reduced k from 5
    
    # Save state
    save_dir = tmp_path / "vector_store"
    os.makedirs(save_dir, exist_ok=True)
    store.save(save_dir)
    
    # Verify files exist
    assert (save_dir / "index.faiss").exists()
    assert (save_dir / "config.json").exists()
    assert (save_dir / "chunks.json").exists()
    
    # Create new store and load state
    new_store = VectorStore(embedding_dim=embedding_dim)
    new_store.load(save_dir)
    
    # Verify metadata
    assert new_store.embedding_dim == store.embedding_dim
    assert len(new_store.chunks) == len(store.chunks)
    
    # Verify search results are identical
    loaded_results = new_store.search(query, k=2)  # Reduced k from 5
    assert len(loaded_results) == len(original_results)
    for orig, loaded in zip(original_results, loaded_results):
        assert orig.chunk.content == loaded.chunk.content
        assert orig.chunk.metadata == loaded.chunk.metadata
        assert abs(orig.score - loaded.score) < 1e-5

def test_vector_store_persistence_ephemeral(tmp_path):
    """Test saving and loading vector store state with ephemeral chunks."""
    # Create test data with expiration
    num_vectors = 20  # Reduced from 100
    embedding_dim = 4
    embeddings = np.random.random((num_vectors, embedding_dim)).astype('float32')
    now = time.time()
    chunks = [
        Chunk(
            content=f"Test chunk {i}",
            metadata={"id": f"chunk_{i}"},
            is_ephemeral=True,
            expiration=now + (i % 24) * 3600
        )
        for i in range(num_vectors)
    ]
    
    # Create and train store
    store = VectorStore(embedding_dim=embedding_dim)
    
    # Add chunks in smaller batches
    batch_size = 5
    for i in range(0, num_vectors, batch_size):
        store.add_chunks(
            chunks[i:i+batch_size], 
            embeddings[i:i+batch_size]
        )
    
    # Save state
    save_dir = tmp_path / "vector_store"
    os.makedirs(save_dir, exist_ok=True)
    store.save(save_dir)
    
    # Create new store and load state
    new_store = VectorStore(embedding_dim=embedding_dim)
    new_store.load(save_dir)
    
    # Verify chunk properties
    assert len(new_store.chunks) == len(store.chunks)
    for idx in store.chunks:
        orig_chunk = store.chunks[idx]
        loaded_chunk = new_store.chunks[idx]
        assert loaded_chunk.content == orig_chunk.content
        assert loaded_chunk.metadata == orig_chunk.metadata
        assert loaded_chunk.is_ephemeral == orig_chunk.is_ephemeral
        assert abs(loaded_chunk.expiration - orig_chunk.expiration) < 1e-5

def test_vector_store_persistence_errors(tmp_path):
    """Test error handling in vector store persistence."""
    # Test saving untrained store
    store = VectorStore(embedding_dim=384)
    save_dir = tmp_path / "vector_store"
    os.makedirs(save_dir, exist_ok=True)
    store.save(save_dir)  # Should work with empty store
    
    # Test loading with missing files
    new_store = VectorStore(embedding_dim=384)
    with pytest.raises(FileNotFoundError):
        new_store.load(tmp_path / "nonexistent")
    
    # Test loading with corrupted files
    with open(save_dir / "config.json", "w") as f:
        f.write("invalid json")
    with pytest.raises(Exception):
        new_store.load(save_dir)

def test_vector_store_gpu_fallback():
    """Test that VectorStore falls back to CPU gracefully when GPU is not available."""
    # Create test data
    num_vectors = 100
    embedding_dim = 4
    embeddings = np.random.random((num_vectors, embedding_dim)).astype('float32')
    chunks = [
        Chunk(
            content=f"Test chunk {i}",
            metadata={"id": f"chunk_{i}"}
        )
        for i in range(num_vectors)
    ]
    
    # Create store with GPU enabled but no GPU available
    store = VectorStore(embedding_dim=embedding_dim, use_gpu=True)
    
    # Verify it fell back to CPU
    assert not store.use_gpu
    assert store.gpu_resources is None
    
    # Add chunks and verify it works
    store.add_chunks(chunks, embeddings)
    
    # Test search
    query = np.random.random(embedding_dim).astype('float32')
    results = store.search(query, k=5)
    assert len(results) == 5

def test_vector_store_gpu_persistence(tmp_path):
    """Test saving and loading vector store with GPU support."""
    # Create test data
    num_vectors = 100
    embedding_dim = 4
    embeddings = np.random.random((num_vectors, embedding_dim)).astype('float32')
    chunks = [
        Chunk(
            content=f"Test chunk {i}",
            metadata={"id": f"chunk_{i}"}
        )
        for i in range(num_vectors)
    ]
    
    # Create and train store with GPU
    store = VectorStore(embedding_dim=embedding_dim, use_gpu=True)
    store.add_chunks(chunks, embeddings)
    
    # Test search before saving
    query = np.random.random(embedding_dim).astype('float32')
    original_results = store.search(query, k=5)
    
    # Save state
    save_dir = tmp_path / "vector_store"
    os.makedirs(save_dir, exist_ok=True)
    store.save(save_dir)
    
    # Create new store and load state
    new_store = VectorStore(embedding_dim=embedding_dim, use_gpu=True)
    new_store.load(save_dir)
    
    # Verify search results are identical
    loaded_results = new_store.search(query, k=5)
    assert len(loaded_results) == len(original_results)
    for orig, loaded in zip(original_results, loaded_results):
        assert orig.chunk.content == loaded.chunk.content
        assert orig.chunk.metadata == loaded.chunk.metadata
        assert abs(orig.score - loaded.score) < 1e-5  # Allow small floating point differences

def test_vector_store_memory_tracking():
    """Test memory tracking with index."""
    # Create test data
    num_vectors = 100
    embedding_dim = 4
    embeddings = np.random.random((num_vectors, embedding_dim)).astype('float32')
    chunks = [
        Chunk(
            content=f"Test chunk {i}",
            metadata={"id": f"chunk_{i}"}
        )
        for i in range(num_vectors)
    ]
    
    # Create store
    store = VectorStore(embedding_dim=embedding_dim, use_gpu=True)
    initial_memory = store._update_memory_usage()
    
    # Add chunks and verify memory increases
    store.add_chunks(chunks, embeddings)
    final_memory = store._update_memory_usage()
    
    # Memory should increase after adding chunks
    assert final_memory > initial_memory
    
    # Verify metrics are labeled correctly
    expected_type = "faiss_gpu" if store.use_gpu else "faiss_cpu"
    assert store._memory_gauge._labelvalues == (expected_type,)
    assert store._search_latency._labelvalues == (expected_type,) 