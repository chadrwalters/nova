from datetime import datetime
from pathlib import Path
import time
from unittest.mock import Mock, patch

import numpy as np
import pytest

from nova.processing.chunking import ChunkingEngine
from nova.processing.embedding import EmbeddingService
from nova.processing.types import Chunk, Document
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
        metadata={"source": "test"},
        source_path=Path("test.md"),
        created_at=datetime.now(),
        modified_at=datetime.now()
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
        Chunk(content="Test chunk 1"),
        Chunk(content="Test chunk 2")
    ]
    
    # Test embedding generation
    service = EmbeddingService(batch_size=2)
    embeddings = service.embed_chunks(chunks)
    
    assert embeddings.shape == (2, 384)
    assert all(c.embedding is not None for c in chunks)
    assert all(c.embedding.shape == (384,) for c in chunks)

def test_vector_store():
    store = VectorStore(embedding_dim=4)
    
    # Create test chunks with embeddings
    chunks = [
        Chunk(
            content="Test 1",
            chunk_id="1",
            embedding=np.array([1, 0, 0, 0], dtype=np.float32)
        ),
        Chunk(
            content="Test 2",
            chunk_id="2",
            embedding=np.array([0, 1, 0, 0], dtype=np.float32)
        )
    ]
    
    # Add chunks
    embeddings = np.vstack([c.embedding for c in chunks])
    store.add_chunks(chunks, embeddings)
    
    # Test search
    query = np.array([1, 0, 0, 0], dtype=np.float32)
    results = store.search(query, k=2)
    
    assert len(results) == 2
    assert results[0].chunk.content == "Test 1"  # Closest match
    assert results[0].score < results[1].score  # Lower score = better match

@patch('time.time')
def test_ephemeral_vector_store(mock_time):
    # Mock time to start at 0
    current_time = 0
    mock_time.return_value = current_time
    
    store = EphemeralVectorStore(
        embedding_dim=4,
        cleanup_interval=1,
        use_cleanup_thread=False  # Disable cleanup thread for testing
    )
    
    # Create test chunks with embeddings and expiration
    chunks = [
        Chunk(
            content="Test 1",
            chunk_id="1",
            embedding=np.array([1, 0, 0, 0], dtype=np.float32),
            is_ephemeral=True,
            expiration=current_time + 2  # Expires in 2 seconds
        ),
        Chunk(
            content="Test 2",
            chunk_id="2",
            embedding=np.array([0, 1, 0, 0], dtype=np.float32),
            is_ephemeral=True,
            expiration=current_time + 0.5  # Expires in 0.5 seconds
        )
    ]
    
    # Add chunks
    embeddings = np.vstack([c.embedding for c in chunks])
    store.add_chunks(chunks, embeddings)
    
    # Test immediate search
    query = np.array([1, 0, 0, 0], dtype=np.float32)
    results = store.search(query, k=2)
    assert len(results) == 2
    
    # Advance time by 1 second
    current_time += 1
    mock_time.return_value = current_time
    
    # Test after first expiration
    results = store.search(query, k=2)
    assert len(results) == 1
    assert results[0].chunk.content == "Test 1"
    
    # Advance time past all expirations
    current_time += 2
    mock_time.return_value = current_time
    
    # Test after all expired
    results = store.search(query, k=2)
    assert len(results) == 0 