"""Vector store for semantic search."""

import json
import logging
import uuid
from typing import Any, Sequence, cast, List, Dict, Optional

import chromadb
import numpy as np
from chromadb.api.models.Collection import Collection
from chromadb.api.types import IncludeEnum, Where, WhereDocument, QueryResult, Embeddings
from sentence_transformers import SentenceTransformer

from nova.vector_store.chunking import Chunk
from nova.vector_store.stats import VectorStoreStats

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector store for semantic search."""

    MODEL_NAME = "paraphrase-MiniLM-L3-v2"
    COLLECTION_NAME = "nova_notes"

    def __init__(self, vector_dir: str, use_memory: bool = False) -> None:
        """Initialize the vector store."""
        self.vector_dir = vector_dir
        self.model: SentenceTransformer | None = None
        self.collection: Collection | None = None
        self.stats = VectorStoreStats(vector_dir=vector_dir)
        self.logger = logging.getLogger(__name__)

        try:
            # Initialize ChromaDB client
            if use_memory:
                self.client = chromadb.Client()
                self.logger.info("Using in-memory ChromaDB client")
            else:
                self.client = chromadb.PersistentClient(path=vector_dir)
                self.logger.info("Using persistent ChromaDB client")

            # Get or create collection
            try:
                self.collection = self.client.get_collection(self.COLLECTION_NAME)
                self.logger.info(f"Using existing collection: {self.COLLECTION_NAME}")
            except Exception:
                self.logger.info(f"Creating new collection: {self.COLLECTION_NAME}")
                self.collection = self.client.create_collection(
                    name=self.COLLECTION_NAME,
                    metadata={
                        "hnsw:space": "cosine",  # Use cosine similarity
                        "hnsw:construction_ef": 200,  # Higher accuracy during construction
                        "hnsw:search_ef": 100,  # Higher accuracy during search
                    }
                )

            # Initialize model
            self.model = SentenceTransformer(self.MODEL_NAME)
            self.logger.info("Vector store initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {e}")
            self.stats.record_error()
            raise

    def add_chunk(self, chunk: Chunk, metadata: dict[str, Any]) -> None:
        """Add a chunk to the vector store."""
        if not self.model or not self.collection:
            self.logger.error("Model or collection not initialized")
            self.stats.record_error()
            raise RuntimeError("Model or collection not initialized")

        try:
            # Generate embedding
            embedding = self.model.encode(chunk.text)

            # Process metadata to ensure correct format for filtering
            processed_metadata: dict[str, str | int | float | bool] = {
                "source": str(chunk.source) if chunk.source else "",
                "heading_text": chunk.heading_text,
                "heading_level": int(chunk.heading_level),
                "tags": json.dumps(chunk.tags),
                "attachments": json.dumps(
                    [{"type": att["type"], "path": att["path"]} for att in chunk.attachments]
                ),
                "chunk_id": str(chunk.chunk_id),
            }

            # Convert embedding to numpy array for ChromaDB
            embedding_array = np.array([embedding.tolist()], dtype=np.float32)

            # Add to collection
            self.collection.add(
                documents=[chunk.text],
                embeddings=embedding_array,  # ChromaDB expects ndarray
                metadatas=[processed_metadata],
                ids=[str(uuid.uuid4())],
            )

            # Update stats
            self.stats.record_chunk_added()
            self.logger.info("Added chunk to vector store")

        except Exception as e:
            self.logger.error(f"Failed to add chunk: {e}")
            self.stats.record_error()
            raise

    def search(
        self,
        query: str,
        limit: int = 5,
        where: Where | None = None,
        include: list[IncludeEnum] | None = None,
    ) -> list[dict[str, Any]]:
        """Search for chunks similar to the query."""
        if not self.model or not self.collection:
            self.logger.error("Model or collection not initialized")
            self.stats.record_error()
            raise RuntimeError("Model or collection not initialized")

        try:
            # Generate query embedding
            query_embedding = self.model.encode(query)

            # Set default include if not specified
            if include is None:
                include = [IncludeEnum.metadatas, IncludeEnum.documents, IncludeEnum.distances]

            # Convert embedding to numpy array for ChromaDB
            embedding_array = np.array([query_embedding.tolist()], dtype=np.float32)

            # Perform search
            results = self.collection.query(
                query_embeddings=embedding_array,  # ChromaDB expects ndarray
                n_results=limit,
                where=where,
                include=include,
            )

            # Process results
            processed_results = []
            if isinstance(results, dict) and "ids" in results and results["ids"]:
                # Extract results safely
                ids = results["ids"]
                documents = results.get("documents", [])
                metadatas = results.get("metadatas", [])
                distances = results.get("distances", [])

                # Ensure we have valid results
                if (
                    isinstance(ids, list)
                    and len(ids) > 0
                    and isinstance(ids[0], list)
                    and len(ids[0]) > 0
                ):
                    # Process each result
                    for i in range(len(ids[0])):
                        result = {
                            "id": ids[0][i],
                            "text": documents[0][i] if documents and len(documents) > 0 else "",
                            "metadata": metadatas[0][i] if metadatas and len(metadatas) > 0 else {},
                            "score": self._normalize_score(
                                float(distances[0][i]) if distances and len(distances) > 0 else 0.0
                            ),
                        }
                        processed_results.append(result)

            # Update stats
            self.stats.record_search(len(processed_results))
            return processed_results

        except Exception as e:
            self.logger.error(f"Search failed: {e}")
            self.stats.record_error()
            raise

    def _normalize_score(self, distance: float) -> float:
        """Normalize the cosine distance to a 0-100 score."""
        # Convert cosine distance to similarity and scale to 0-100
        similarity = 1 - distance
        return round(similarity * 100, 2)

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.collection:
                self.client.delete_collection(self.COLLECTION_NAME)
                self.logger.info(f"Deleted collection: {self.COLLECTION_NAME}")
        except Exception as e:
            self.logger.error(f"Failed to cleanup vector store: {e}")
            self.stats.record_error()
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        if hasattr(self, "stats") and self.stats:
            return self.stats.get_stats()
        return {}
