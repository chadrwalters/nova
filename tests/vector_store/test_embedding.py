"""Tests for the embedding engine."""
import tempfile
import numpy as np
import pytest
from pytest import FixtureRequest
from nova.vector_store.embedding import EmbeddingEngine, EmbeddingResult


@pytest.fixture(scope="function")
def sample_texts(_request: FixtureRequest) -> list[str]:
    """Sample texts for testing embeddings."""
    return [
        "This is the first test document.",
        "Here is another document with different content.",
        "A third document that should get its own embedding.",
        "Finally, a fourth document to test batch processing.",
    ]


@pytest.fixture(scope="function")
def engine(_request: FixtureRequest) -> EmbeddingEngine:
    """Create an EmbeddingEngine instance for testing."""
    return EmbeddingEngine(batch_size=2)  # Small batch size for testing


def test_embedding_engine_initialization() -> None:
    """Test initialization of EmbeddingEngine."""
    engine = EmbeddingEngine(
        model_name="all-MiniLM-L6-v2", batch_size=32, cache_dir=None
    )
    assert engine.model_name == "all-MiniLM-L6-v2"
    assert engine.batch_size == 32
    assert engine.cache_dir is None


def test_embedding_generation(engine: EmbeddingEngine, sample_texts: list[str]) -> None:
    """Test generation of embeddings."""
    results = engine.embed_texts(sample_texts, use_cache=False)

    # Check we got the right number of results
    assert len(results) == len(sample_texts)

    # Check each result
    for result in results:
        assert isinstance(result, EmbeddingResult)
        assert isinstance(result.embedding, np.ndarray)
        assert result.model_name == engine.model_name
        assert len(result.cache_key) > 0


def test_embedding_dimensions(engine: EmbeddingEngine) -> None:
    """Test embedding dimensions."""
    text = "Test document for embedding dimension check."
    results = engine.embed_texts([text], use_cache=False)

    # MiniLM-L6-v2 produces 384-dimensional embeddings
    assert results[0].embedding.shape == (384,)


def test_batched_processing(engine: EmbeddingEngine, sample_texts: list[str]) -> None:
    """Test batched processing of texts."""
    # With batch_size=2, this should take 2 batches
    results = engine.embed_texts(sample_texts[:3], use_cache=False)

    assert len(results) == 3
    for result in results:
        assert isinstance(result.embedding, np.ndarray)


def test_cache_key_generation(engine: EmbeddingEngine) -> None:
    """Test cache key generation."""
    text = "Test document for cache key generation."
    key1 = engine._compute_cache_key(text)
    key2 = engine._compute_cache_key(text)

    # Same text should produce same key
    assert key1 == key2

    # Different text should produce different key
    different_key = engine._compute_cache_key("Different text")
    assert key1 != different_key


def test_caching(engine: EmbeddingEngine, sample_texts: list[str]) -> None:
    """Test caching functionality."""
    # First run with cache
    results1 = engine.embed_texts(sample_texts, use_cache=True)

    # Second run with same texts
    results2 = engine.embed_texts(sample_texts, use_cache=True)

    # Results should be identical
    for r1, r2 in zip(results1, results2):
        assert np.array_equal(r1.embedding, r2.embedding)
        assert r1.cache_key == r2.cache_key


def test_cache_persistence() -> None:
    """Test cache persistence."""
    with tempfile.TemporaryDirectory() as cache_dir:
        # Create engine with cache directory
        engine1 = EmbeddingEngine(cache_dir=cache_dir)

        # Generate some embeddings
        texts = ["Test document one.", "Test document two."]
        results1 = engine1.embed_texts(texts, use_cache=True)

        # Create new engine with same cache directory
        engine2 = EmbeddingEngine(cache_dir=cache_dir)

        # Generate embeddings for same texts
        results2 = engine2.embed_texts(texts, use_cache=True)

        # Results should be identical
        for r1, r2 in zip(results1, results2):
            assert np.array_equal(r1.embedding, r2.embedding)
            assert r1.cache_key == r2.cache_key
