"""Performance tests for Nova system components."""

import asyncio
import time
import psutil
from pathlib import Path
from typing import List

import pytest
from nova.ingestion import BearExportHandler, DoclingConverter
from nova.processing.chunking import ChunkingEngine
from nova.processing import EmbeddingService
from nova.processing.vector_store import VectorStore, EphemeralVectorStore
from nova.rag import RAGOrchestrator
from nova.types import Document, Chunk, MCPPayload
import numpy as np

# Test configuration
LARGE_DATASET_SIZE = 1000  # Number of documents for large dataset test
CHUNK_SIZE = 500  # Size of chunks for testing
QUERY_COUNT = 100  # Number of queries for response time testing
MEMORY_THRESHOLD_MB = 2048  # Maximum allowed memory usage in MB


def generate_test_documents(count: int) -> List[Document]:
    """Generate test documents with realistic content."""
    documents = []
    for i in range(count):
        content = f"Document {i}\n\n"
        content += "# Heading 1\n\n"
        content += "Lorem ipsum " * 100  # Approximately 500 words
        content += "\n\n## Heading 2\n\n"
        content += "Dolor sit amet " * 100
        
        doc = Document(
            content=content,
            metadata={"id": f"doc_{i}", "type": "test"},
            source_path=Path(f"test_doc_{i}.md")
        )
        documents.append(doc)
    return documents


@pytest.mark.asyncio
@pytest.mark.performance
async def test_chunking_performance():
    """Test chunking performance with large dataset."""
    # Setup
    chunker = ChunkingEngine()
    documents = generate_test_documents(LARGE_DATASET_SIZE)
    
    # Measure chunking time
    start_time = time.time()
    all_chunks = []
    for doc in documents:
        chunks = chunker.chunk_document(doc, chunk_size=CHUNK_SIZE)
        all_chunks.extend(chunks)
    end_time = time.time()
    
    # Assert performance metrics
    processing_time = end_time - start_time
    chunks_per_second = len(all_chunks) / processing_time
    
    assert processing_time < LARGE_DATASET_SIZE * 0.1  # Less than 0.1s per document
    assert chunks_per_second > 10  # At least 10 chunks per second


@pytest.mark.asyncio
@pytest.mark.performance
async def test_embedding_performance():
    """Test embedding generation performance."""
    # Setup
    embedder = EmbeddingService()
    chunks = [
        Chunk(
            content=f"Test chunk {i} with sufficient content for embedding",
            metadata={"id": f"chunk_{i}"}
        )
        for i in range(100)
    ]
    
    # Measure embedding time
    start_time = time.time()
    embeddings = await embedder.embed_chunks(chunks)
    end_time = time.time()
    
    # Assert performance metrics
    processing_time = end_time - start_time
    embeddings_per_second = len(embeddings) / processing_time
    
    assert processing_time < len(chunks) * 0.1  # Less than 0.1s per chunk
    assert embeddings_per_second > 5  # At least 5 embeddings per second


@pytest.mark.asyncio
@pytest.mark.performance
async def test_vector_store_performance():
    """Test vector store search performance."""
    # Setup
    store = VectorStore(embedding_dim=4)  # Use small dimension for stability
    chunks = [
        Chunk(
            content=f"Test chunk {i} with sufficient content for embedding",
            metadata={"id": f"chunk_{i}"}
        )
        for i in range(1000)  # Reduced dataset size
    ]
    
    # Generate simple embeddings
    embeddings = np.random.random((len(chunks), 4)).astype('float32')
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    
    # Measure indexing time
    start_time = time.time()
    batch_size = 100
    for i in range(0, len(chunks), batch_size):
        end = min(i + batch_size, len(chunks))
        store.add_chunks(chunks[i:end], embeddings[i:end])
    indexing_time = time.time() - start_time
    
    # Measure search time with different k values
    query_embedding = embeddings[0]  # Use first embedding as query
    search_times = {k: [] for k in [5, 10]}  # Reduced k values
    
    for k in search_times.keys():
        for _ in range(10):  # Reduced query count
            start_time = time.time()
            results = store.search(query_embedding, k=k)
            search_times[k].append(time.time() - start_time)
            # Verify k-nearest neighbors
            assert len(results) == k  # Changed from <= to ==
    
    # Assert performance metrics
    assert indexing_time < 10.0  # Less than 10 seconds for indexing
    
    for k, times in search_times.items():
        avg_search_time = sum(times) / len(times)
        assert avg_search_time < 0.01  # Less than 10ms per search


@pytest.mark.asyncio
@pytest.mark.performance
async def test_rag_performance():
    """Test end-to-end RAG performance."""
    # Setup
    orchestrator = RAGOrchestrator()
    
    # Generate test queries
    queries = [
        f"Test query {i} that should retrieve relevant information"
        for i in range(QUERY_COUNT)
    ]
    
    # Measure query processing time
    processing_times = []
    
    for query in queries:
        start_time = time.time()
        response = await orchestrator.process_query(query)
        processing_times.append(time.time() - start_time)
    
    # Assert performance metrics
    avg_processing_time = sum(processing_times) / len(processing_times)
    assert avg_processing_time < 5  # Less than 5 seconds per query


@pytest.mark.performance
def test_memory_usage():
    """Test memory usage under load."""
    import psutil
    import os
    
    def get_memory_mb():
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024
    
    # Record baseline memory
    baseline_memory = get_memory_mb()
    
    # Generate large dataset
    documents = generate_test_documents(LARGE_DATASET_SIZE)
    
    # Process documents
    chunker = ChunkingEngine()
    chunks = []
    for doc in documents:
        doc_chunks = chunker.chunk_document(doc)
        chunks.extend(doc_chunks)
    
    # Check memory after processing
    final_memory = get_memory_mb()
    memory_increase = final_memory - baseline_memory
    
    assert memory_increase < MEMORY_THRESHOLD_MB  # Less than 2GB increase


@pytest.mark.asyncio
@pytest.mark.performance
async def test_ephemeral_data_handling():
    """Test ephemeral data handling performance."""
    from nova.processing import EphemeralVectorStore
    
    # Setup with simple parameters
    store = EphemeralVectorStore(
        embedding_dim=4  # Small dimension for stability
    )
    
    # Create chunks with staggered expiration
    chunks = []
    now = time.time()
    for i in range(100):  # Reduced dataset size
        chunks.append(Chunk(
            content=f"Ephemeral chunk {i}",
            metadata={"id": f"chunk_{i}"},
            is_ephemeral=True,
            expiration=now + (i % 5)  # Expire in 0-4 seconds
        ))
    
    # Generate simple embeddings
    embeddings = np.random.random((len(chunks), 4)).astype('float32')
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    embeddings = embeddings / norms
    
    # Measure add time
    start_time = time.time()
    batch_size = 10
    for i in range(0, len(chunks), batch_size):
        end = min(i + batch_size, len(chunks))
        store.add_chunks(chunks[i:end], embeddings[i:end])
    add_time = time.time() - start_time
    
    # Measure search time before expiration
    query_embedding = embeddings[0]
    initial_search_times = []
    for _ in range(5):  # Reduced query count
        start_time = time.time()
        results = store.search(query_embedding, k=5)
        initial_search_times.append(time.time() - start_time)
    
    # Wait for some chunks to expire
    await asyncio.sleep(2)
    
    # Measure cleanup time
    start_time = time.time()
    store._cleanup_expired()  # Force cleanup
    cleanup_time = time.time() - start_time
    
    # Measure search time after cleanup
    post_cleanup_search_times = []
    for _ in range(5):  # Reduced query count
        start_time = time.time()
        results = store.search(query_embedding, k=5)
        post_cleanup_search_times.append(time.time() - start_time)
    
    # Assert performance metrics
    assert add_time < 2.0  # Less than 2 seconds to add chunks
    assert cleanup_time < 0.5  # Less than 500ms to clean up
    
    avg_initial_search = sum(initial_search_times) / len(initial_search_times)
    avg_post_cleanup_search = sum(post_cleanup_search_times) / len(post_cleanup_search_times)
    
    assert avg_initial_search < 0.01  # Less than 10ms per search
    assert avg_post_cleanup_search < 0.01  # Search time should remain fast after cleanup
    
    # Verify memory usage
    process = psutil.Process()
    memory_mb = process.memory_info().rss / 1024 / 1024
    assert memory_mb < MEMORY_THRESHOLD_MB  # Memory usage should stay under threshold 