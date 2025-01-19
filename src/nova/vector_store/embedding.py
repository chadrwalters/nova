"""Embedding engine for text processing."""

import logging
from dataclasses import dataclass

import numpy as np
from chromadb.api.types import Documents, Embedding, EmbeddingFunction, Embeddings
from numpy.typing import NDArray
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)


@dataclass
class EmbeddingResult:
    """Result of embedding text."""

    def __init__(
        self, text: str, vector: NDArray[np.float32], metadata: dict | None = None
    ) -> None:
        """Initialize embedding result.

        Args:
            text: Original text
            vector: Embedding vector
            metadata: Optional metadata
        """
        self.text = text
        self.vector = vector
        self.metadata = metadata or {}


class NovaEmbeddingFunction(EmbeddingFunction):
    """ChromaDB embedding function implementation."""

    def __init__(self) -> None:
        """Initialize the embedding function."""
        self.engine = EmbeddingEngine()

    def __call__(self, input: Documents) -> Embeddings:
        """Create embeddings for texts.

        Args:
            input: Sequence of texts to embed

        Returns:
            List of embeddings as numpy arrays
        """
        results = self.engine.embed_texts(list(input))
        # Convert to list of numpy arrays as required by ChromaDB
        embeddings: list[Embedding] = [result.vector for result in results]
        return embeddings


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
        vectors = embeddings.astype(np.float32)
        return [
            EmbeddingResult(text=text, vector=vector)
            for text, vector in zip(texts, vectors, strict=False)
        ]
