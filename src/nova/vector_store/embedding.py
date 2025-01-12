"""Embedding engine for converting text into vector representations."""
import hashlib
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import numpy.typing as npt
import torch
from sentence_transformers import SentenceTransformer


@dataclass
class EmbeddingResult:
    """Result of embedding a text."""

    embedding: npt.NDArray[np.float32]
    model_name: str
    cache_key: str


class EmbeddingEngine:
    """Engine for converting text into vector representations."""

    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        batch_size: int = 32,
        cache_dir: str | None = None,
    ) -> None:
        """Initialize the embedding engine.

        Args:
            model_name: Name of the sentence transformer model to use.
            batch_size: Number of texts to process at once.
            cache_dir: Directory to store cached embeddings. If None, no caching is used.
        """
        self.model_name = model_name
        self.batch_size = batch_size
        self.cache_dir = cache_dir

        # Initialize model
        self.model = SentenceTransformer(model_name)

        # Initialize cache
        self._cache: dict[str, npt.NDArray[np.float32]] = {}
        if cache_dir is not None:
            self._load_cache()

    def embed_texts(
        self, texts: list[str], use_cache: bool = True
    ) -> list[EmbeddingResult]:
        """Convert texts into vector representations.

        Args:
            texts: List of texts to embed.
            use_cache: Whether to use cached embeddings if available.

        Returns:
            List of embedding results, one for each input text.
        """
        results: list[EmbeddingResult] = []
        texts_to_embed: list[str] = []
        cache_keys: list[str] = []

        # Check cache first if enabled
        if use_cache and self.cache_dir is not None:
            for text in texts:
                cache_key = self._compute_cache_key(text)
                if cache_key in self._cache:
                    results.append(
                        EmbeddingResult(
                            embedding=self._cache[cache_key],
                            model_name=self.model_name,
                            cache_key=cache_key,
                        )
                    )
                else:
                    texts_to_embed.append(text)
                    cache_keys.append(cache_key)
        else:
            texts_to_embed = texts
            cache_keys = [self._compute_cache_key(text) for text in texts]

        # Embed any remaining texts
        if texts_to_embed:
            # Process in batches
            for i in range(0, len(texts_to_embed), self.batch_size):
                batch = texts_to_embed[i : i + self.batch_size]
                batch_keys = cache_keys[i : i + self.batch_size]

                # Generate embeddings
                embeddings = self.model.encode(
                    batch,
                    convert_to_tensor=True,
                    show_progress_bar=False,
                )

                # Convert to numpy and store results
                for text_embedding, cache_key in zip(embeddings, batch_keys):
                    # Convert to numpy array if it's a tensor
                    if isinstance(text_embedding, torch.Tensor):
                        text_embedding = text_embedding.cpu().numpy()

                    # Store in cache if enabled
                    if use_cache and self.cache_dir is not None:
                        self._cache[cache_key] = text_embedding

                    results.append(
                        EmbeddingResult(
                            embedding=text_embedding,
                            model_name=self.model_name,
                            cache_key=cache_key,
                        )
                    )

        # Save cache if it was used
        if use_cache and self.cache_dir is not None:
            self._save_cache()

        return results

    def _compute_cache_key(self, text: str) -> str:
        """Compute a cache key for a text.

        Args:
            text: The text to compute a cache key for.

        Returns:
            A unique cache key for the text.
        """
        # Combine text and model name to ensure cache is model-specific
        key_input = f"{text}:{self.model_name}"
        return hashlib.sha256(key_input.encode()).hexdigest()

    def _load_cache(self) -> None:
        """Load cached embeddings from disk."""
        if self.cache_dir is None:
            return

        cache_file = Path(self.cache_dir) / f"{self.model_name}_cache.npz"
        if cache_file.exists():
            arrays_dict = dict(np.load(str(cache_file)))
            self._cache = {str(key): value for key, value in arrays_dict.items()}

    def _save_cache(self) -> None:
        """Save cached embeddings to disk."""
        if self.cache_dir is None:
            return

        # Create cache directory if it doesn't exist
        cache_dir = Path(self.cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)

        # Save cache
        cache_file = cache_dir / f"{self.model_name}_cache.npz"
        if self._cache:
            # Create a temporary file to avoid any potential race conditions
            temp_file = cache_file.with_suffix(".tmp")
            try:
                # Save to temporary file first
                with open(temp_file, "wb") as f:
                    # Create a structured array with the cache data
                    data = np.array(
                        [(k, v) for k, v in self._cache.items()],
                        dtype=[("key", "U100"), ("value", "O")],
                    )
                    np.save(f, data)
                # Rename to final location
                temp_file.replace(cache_file)
            finally:
                # Clean up temp file if it still exists
                if temp_file.exists():
                    temp_file.unlink()
