"""Tests for the embedding engine."""

import numpy as np

from nova.vector_store.embedding import EmbeddingEngine


def test_embed_text_basic() -> None:
    """Test basic text embedding."""
    engine = EmbeddingEngine()
    text = "This is a test document."
    result = engine.embed_text(text)

    assert result.text == text
    assert isinstance(result.vector, np.ndarray)
    assert result.vector.dtype == np.float32
    assert result.vector.shape == (384,)


def test_embed_texts_multiple() -> None:
    """Test embedding multiple texts."""
    engine = EmbeddingEngine()
    texts = ["This is document 1.", "This is document 2.", "This is document 3."]
    results = engine.embed_texts(texts)

    assert len(results) == len(texts)
    for text, result in zip(texts, results, strict=False):
        assert result.text == text
        assert isinstance(result.vector, np.ndarray)
        assert result.vector.dtype == np.float32
        assert result.vector.shape == (384,)


def test_embed_text_empty() -> None:
    """Test embedding empty text."""
    engine = EmbeddingEngine()
    text = ""
    result = engine.embed_text(text)

    assert result.text == text
    assert isinstance(result.vector, np.ndarray)
    assert result.vector.dtype == np.float32
    assert result.vector.shape == (384,)
