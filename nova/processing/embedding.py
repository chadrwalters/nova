from typing import List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

from nova.processing.types import Chunk


class EmbeddingService:
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        device: Optional[str] = None,
        batch_size: int = 32
    ):
        """Initialize the embedding service.
        
        Args:
            model_name: Name of the sentence-transformers model to use
            device: Device to run model on ('cpu', 'cuda', etc.)
            batch_size: Batch size for embedding generation
        """
        self.model = SentenceTransformer(model_name, device=device)
        self.batch_size = batch_size
        self.embedding_dim = self.model.get_sentence_embedding_dimension()
    
    def embed_chunks(self, chunks: List[Chunk]) -> np.ndarray:
        """Generate embeddings for a list of chunks.
        
        Args:
            chunks: List of chunks to embed
        
        Returns:
            Array of embeddings with shape (n_chunks, embedding_dim)
        """
        # Extract text from chunks
        texts = [chunk.content for chunk in chunks]
        
        # Generate embeddings in batches
        embeddings = []
        for i in range(0, len(texts), self.batch_size):
            batch_texts = texts[i:i + self.batch_size]
            batch_embeddings = self.model.encode(
                batch_texts,
                convert_to_numpy=True,
                normalize_embeddings=True
            )
            embeddings.append(batch_embeddings)
        
        # Combine batches
        all_embeddings = np.vstack(embeddings)
        
        # Update chunks with embeddings
        for chunk, embedding in zip(chunks, all_embeddings):
            chunk.embedding = embedding
        
        return all_embeddings
    
    def embed_text(self, text: str) -> np.ndarray:
        """Generate embedding for a single text.
        
        Args:
            text: Text to embed
        
        Returns:
            Embedding array with shape (embedding_dim,)
        """
        return self.model.encode(
            text,
            convert_to_numpy=True,
            normalize_embeddings=True
        )
    
    def embed_texts(self, texts: List[str]) -> np.ndarray:
        """Generate embeddings for a list of texts.
        
        Args:
            texts: List of texts to embed
        
        Returns:
            Array of embeddings with shape (n_texts, embedding_dim)
        """
        return self.model.encode(
            texts,
            convert_to_numpy=True,
            normalize_embeddings=True,
            batch_size=self.batch_size
        ) 