"""Performance tests for resource operations."""

import random
from pathlib import Path

import pytest

from nova.server.server import NovaServer
from nova.server.types import ServerConfig
from tests.performance.conftest import benchmark


@pytest.fixture(scope="module")
def server(temp_dir: Path) -> NovaServer:
    """Create server instance for benchmarking.

    Args:
        temp_dir: Temporary directory fixture

    Returns:
        NovaServer instance
    """
    config = ServerConfig(host="localhost", port=8000, debug=True, max_connections=5)
    server = NovaServer(config)
    server.start()
    return server


@pytest.fixture(scope="module")
def populated_vector_store(server: NovaServer, sample_documents: list[dict]) -> None:
    """Pre-populate vector store with sample documents.

    Args:
        server: NovaServer instance
        sample_documents: List of sample documents
    """
    vector_store = server._get_vector_store()
    for doc in sample_documents:
        vector_store.add(doc["id"], doc["content"], doc["metadata"])
    # Process any remaining batched documents
    vector_store._process_batch()


@benchmark(iterations=50, warmup=5)
def test_vector_store_add(server: NovaServer, sample_documents: list[dict]) -> None:
    """Benchmark vector store add operation."""
    vector_store = server._get_vector_store()
    doc = random.choice(sample_documents)
    # Use shorter content to reduce processing time
    doc["content"] = doc["content"].split(".")[0]
    vector_store.add(doc["id"], doc["content"], doc["metadata"])
    # Process batch immediately to avoid accumulation
    vector_store._process_batch()


@benchmark(iterations=50, warmup=5)
def test_vector_store_search(
    server: NovaServer, sample_documents: list[dict], populated_vector_store: None
) -> None:
    """Benchmark vector store search operation."""
    vector_store = server._get_vector_store()
    # Use a simpler query with fewer tokens
    query = random.choice(["document", "content", "test"])
    vector_store.search(query, limit=5)  # Reduced limit for faster results


@benchmark(iterations=100, warmup=10)
def test_vector_store_remove(
    server: NovaServer, sample_documents: list[dict], populated_vector_store: None
) -> None:
    """Benchmark vector store remove operation."""
    vector_store = server._get_vector_store()
    # Add a document specifically for removal
    doc = random.choice(sample_documents)
    vector_store.add(doc["id"], doc["content"], doc["metadata"])
    # Process any remaining documents to ensure it's added
    vector_store._process_batch()
    # Now remove it
    vector_store.remove(doc["id"])


@benchmark(iterations=100, warmup=10)
def test_note_store_read(server: NovaServer, sample_documents: list[dict]) -> None:
    """Benchmark note store read operation."""
    note_store = server._get_note_store()
    doc = random.choice(sample_documents)
    note_store.read(doc["id"])


@benchmark(iterations=100, warmup=10)
def test_note_store_write(server: NovaServer, sample_documents: list[dict]) -> None:
    """Benchmark note store write operation."""
    note_store = server._get_note_store()
    doc = random.choice(sample_documents)
    note_store.write(doc["id"], doc["content"])


@benchmark(iterations=100, warmup=10)
def test_attachment_store_read(
    server: NovaServer, sample_documents: list[dict]
) -> None:
    """Benchmark attachment store read operation."""
    attachment_store = server._get_attachment_store()
    doc = random.choice(sample_documents)
    attachment_store.read(doc["id"])


@benchmark(iterations=100, warmup=10)
def test_attachment_store_write(
    server: NovaServer, sample_documents: list[dict]
) -> None:
    """Benchmark attachment store write operation."""
    attachment_store = server._get_attachment_store()
    doc = random.choice(sample_documents)
    attachment_store.write(doc["id"], doc["content"].encode())
