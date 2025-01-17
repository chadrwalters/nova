"""Embedding engine for text processing."""

import logging
from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of text embedding."""

    text: str
    vector: NDArray[np.float32]


class EmbeddingEngine:
    """Engine for creating text embeddings."""

    def __init__(self) -> None:
        """Initialize the embedding engine."""
        self.model = SentenceTransformer("paraphrase-MiniLM-L3-v2")

    def embed_text(self, text: str) -> EmbeddingResult:
        """Create embedding for a single text.

        Args:
            text: Text to embed

        Returns:
            Embedding result
        """
        # Create embedding using sentence transformer
        embedding = self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        if not isinstance(embedding, np.ndarray):
            embedding = np.array(embedding)
        vector = embedding.astype(np.float32)
        return EmbeddingResult(text=text, vector=vector)

    def embed_texts(self, texts: list[str]) -> list[EmbeddingResult]:
        """Create embeddings for multiple texts.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding results
        """
        # Create embeddings in batch
        embeddings = self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=32,
        )
        if not isinstance(embeddings, np.ndarray):
            embeddings = np.array(embeddings)
        vectors = embeddings.astype(np.float32)
        return [
            EmbeddingResult(text=text, vector=vector)
            for text, vector in zip(texts, vectors, strict=False)
        ]
