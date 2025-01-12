"""Tests for the vector store."""
import tempfile
from collections.abc import Generator
import numpy as np
import numpy.typing as npt
import pytest
from pytest import FixtureRequest
from nova.vector_store.store import VectorStore
from nova.vector_store.chunking import Chunk


@pytest.fixture(scope="function")
def store_path(_request: FixtureRequest) -> Generator[str, None, None]:
    """Create a temporary directory for the vector store."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield temp_dir


@pytest.fixture(scope="function")
def store(store_path: str, _request: FixtureRequest) -> VectorStore:
    """Create a VectorStore instance for testing."""
    return VectorStore(
        persistent_path=store_path,
        collection_name="test_collection",
        distance_func="cosine",
    )


@pytest.fixture(scope="function")
def sample_chunks(_request: FixtureRequest) -> list[Chunk]:
    """Create sample chunks for testing."""
    return [
        Chunk(
            content="First test chunk with some content.",
            source_location="test1.md",
            tags=["test", "first"],
            heading_context=["Main", "Section 1"],
            start_line=1,
            end_line=3,
        ),
        Chunk(
            content="Second chunk with different content.",
            source_location="test1.md",
            tags=["test", "second"],
            heading_context=["Main", "Section 2"],
            start_line=4,
            end_line=6,
        ),
        Chunk(
            content="Third chunk from a different file.",
            source_location="test2.md",
            tags=["test", "third"],
            heading_context=["Other", "Section 1"],
            start_line=1,
            end_line=2,
        ),
    ]


@pytest.fixture(scope="function")
def sample_embeddings(_request: FixtureRequest) -> list[npt.NDArray[np.float32]]:
    """Create sample embeddings for testing."""
    # Create random embeddings for testing
    return [
        np.random.rand(384).astype(np.float32)  # Match MiniLM dimensions
        for _ in range(3)
    ]


def test_store_initialization(store: VectorStore) -> None:
    """Test initialization of VectorStore."""
    assert store.collection_name == "test_collection"
    assert store.distance_func == "cosine"
    assert store.persistent_collection is not None
    assert store.ephemeral_collection is not None


def test_chunk_metadata_conversion(
    store: VectorStore, sample_chunks: list[Chunk]
) -> None:
    """Test chunk metadata conversion."""
    chunk = sample_chunks[0]

    # Convert to metadata
    metadata = store._chunk_to_metadata(chunk)
    assert metadata["source"] == chunk.source_location
    assert metadata["tags"] == ",".join(chunk.tags)
    assert metadata["heading_context"] == ",".join(chunk.heading_context)
    assert metadata["start_line"] == chunk.start_line
    assert metadata["end_line"] == chunk.end_line

    # Convert back to chunk
    reconstructed = store._metadata_to_chunk(chunk.content, metadata)
    assert reconstructed.content == chunk.content
    assert reconstructed.source_location == chunk.source_location
    assert reconstructed.tags == chunk.tags
    assert reconstructed.heading_context == chunk.heading_context
    assert reconstructed.start_line == chunk.start_line
    assert reconstructed.end_line == chunk.end_line


def test_add_persistent_chunks(
    store: VectorStore,
    sample_chunks: list[Chunk],
    sample_embeddings: list[npt.NDArray[np.float32]],
) -> None:
    """Test adding persistent chunks."""
    # Add chunks
    store.add_chunks(sample_chunks, sample_embeddings, is_ephemeral=False)

    # Search with first embedding
    results = store.search(sample_embeddings[0], limit=1, include_ephemeral=False)

    # Should find the first chunk
    assert len(results) == 1
    assert results[0].chunk.content == sample_chunks[0].content
    assert results[0].score > 0.9  # Should be very similar to itself


def test_add_ephemeral_chunks(
    store: VectorStore,
    sample_chunks: list[Chunk],
    sample_embeddings: list[npt.NDArray[np.float32]],
) -> None:
    """Test adding ephemeral chunks."""
    # Add chunks
    store.add_chunks(sample_chunks, sample_embeddings, is_ephemeral=True)

    # Search with first embedding
    results = store.search(sample_embeddings[0], limit=1, include_ephemeral=True)

    # Should find the first chunk
    assert len(results) == 1
    assert results[0].chunk.content == sample_chunks[0].content

    # Clear ephemeral and search again
    store.clear_ephemeral()
    results = store.search(sample_embeddings[0], limit=1, include_ephemeral=True)
    assert len(results) == 0


def test_combined_search(
    store: VectorStore,
    sample_chunks: list[Chunk],
    sample_embeddings: list[npt.NDArray[np.float32]],
) -> None:
    """Test combined search functionality."""
    # Add some chunks to persistent storage
    store.add_chunks(sample_chunks[:2], sample_embeddings[:2], is_ephemeral=False)

    # Add one chunk to ephemeral storage
    store.add_chunks(sample_chunks[2:], sample_embeddings[2:], is_ephemeral=True)

    # Search with limit high enough to find all chunks
    results = store.search(sample_embeddings[0], limit=3, include_ephemeral=True)

    # Should find all chunks
    assert len(results) == 3

    # Results should be ordered by similarity
    assert results[0].score >= results[1].score
    assert results[1].score >= results[2].score


def test_min_score_filtering(
    store: VectorStore,
    sample_chunks: list[Chunk],
    sample_embeddings: list[npt.NDArray[np.float32]],
) -> None:
    """Test minimum score filtering."""
    # Add chunks
    store.add_chunks(sample_chunks, sample_embeddings, is_ephemeral=False)

    # Search with high min_score
    results = store.search(
        sample_embeddings[0],
        limit=10,
        min_score=0.95,
        include_ephemeral=False,
    )

    # Should only find very similar chunks
    assert all(r.score >= 0.95 for r in results)
