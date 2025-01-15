"""Vector store implementation using Chroma."""

import logging
import time
import os
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Union, cast

import numpy as np
from numpy.typing import NDArray
import chromadb  # type: ignore[import]
from chromadb.api.types import Embeddings, Metadatas, Where  # type: ignore[import]
from chromadb.config import Settings  # type: ignore[import]
from sentence_transformers import SentenceTransformer  # type: ignore

from .types import VectorStoreStats

logger = logging.getLogger(__name__)

# Use a smaller, faster model
MODEL_NAME = "paraphrase-MiniLM-L3-v2"
BATCH_SIZE = 32


class VectorStore:
    """Vector store for embeddings."""

    def __init__(self, store_dir: Path) -> None:
        """Initialize vector store.

        Args:
            store_dir: Directory for storing vector data
        """
        self._store_dir = store_dir
        self._store_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(self._store_dir, 0o755)  # rwxr-xr-x

        # Create ChromaDB directory structure with proper permissions
        chroma_dir = self._store_dir / "chroma"
        chroma_dir.mkdir(parents=True, exist_ok=True)
        os.chmod(chroma_dir, 0o755)  # rwxr-xr-x

        # Create all required subdirectories
        subdirs = ["db", "index", "system", "data"]
        for subdir in subdirs:
            dir_path = chroma_dir / subdir
            dir_path.mkdir(parents=True, exist_ok=True)
            os.chmod(dir_path, 0o755)  # rwxr-xr-x

        # Create and set permissions for SQLite database file
        db_file = chroma_dir / "chroma.db"
        if not db_file.exists():
            db_file.touch(mode=0o644)  # rw-r--r--
        os.chmod(db_file, 0o644)  # rw-r--r--

        # Initialize other instance variables
        self._model: SentenceTransformer | None = None
        self._embedding_cache: dict[str, NDArray[np.float32]] = {}
        self._batch_queue: list[tuple[str, str, dict[str, Any]]] = []

        # Configure Chroma client with reset enabled for tests
        settings = Settings(
            allow_reset=True,
            is_persistent=True,
            persist_directory=str(chroma_dir),
            anonymized_telemetry=False,
        )

        # Initialize ChromaDB client and collection
        self.client = chromadb.Client(settings)
        self.collection = self.client.get_or_create_collection("nova")

    @property
    def model(self) -> SentenceTransformer:
        """Get or initialize the sentence transformer model."""
        if self._model is None:
            self._model = SentenceTransformer(MODEL_NAME)
        return self._model

    def add(self, doc_id: str, content: str, metadata: dict[str, Any]) -> None:
        """Add a document to the store.

        Args:
            doc_id: Document ID
            content: Document content
            metadata: Document metadata
        """
        # Add to batch queue
        self._batch_queue.append((doc_id, content, metadata))

        # Process batch if queue is full
        if len(self._batch_queue) >= BATCH_SIZE:
            self._process_batch()

    def _process_batch(self) -> None:
        """Process batched documents."""
        if not self._batch_queue:
            return

        # Convert documents to embeddings
        texts = [doc[1] for doc in self._batch_queue]  # content is at index 1
        embeddings = self.model.encode(texts)

        # Add to Chroma collection
        self.collection.add(
            embeddings=embeddings,
            documents=texts,
            metadatas=[doc[2] for doc in self._batch_queue],  # metadata is at index 2
            ids=[doc[0] for doc in self._batch_queue],  # id is at index 0
        )

        # Clear batch
        self._batch_queue.clear()

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for similar documents.

        Args:
            query: Query string
            limit: Maximum number of results

        Returns:
            List of results with metadata
        """
        # Process any remaining documents
        if self._batch_queue:
            self._process_batch()

        # Generate query embedding
        query_vector = self.model.encode([query], convert_to_numpy=True)
        if not isinstance(query_vector, np.ndarray):
            query_vector = np.array(query_vector)
        query_vector = query_vector.astype(np.float32).reshape(-1)
        return self.query(query_vector, n_results=limit)

    def remove(self, doc_id: str) -> None:
        """Remove a document from the store.

        Args:
            doc_id: Document ID to remove

        Raises:
            ValueError: If document ID doesn't exist
        """
        # Process any remaining documents
        if self._batch_queue:
            self._process_batch()

        # Check if document exists
        results = self.collection.get(ids=[doc_id])
        if not results["ids"]:
            raise ValueError(f"Document {doc_id} not found")

        self.collection.delete(ids=[doc_id])
        if doc_id in self._embedding_cache:
            del self._embedding_cache[doc_id]
        logger.info("Removed document %s", doc_id)

    def add_embeddings(
        self,
        embedding_vectors: list[NDArray[np.float32]],
        metadata_dicts: list[dict[str, str | int | float | bool]],
    ) -> None:
        """Add embeddings to the store.

        Args:
            embedding_vectors: List of embedding vectors
            metadata_dicts: List of metadata dictionaries
        """
        # Convert numpy arrays to lists
        embeddings: Embeddings = [vector.tolist() for vector in embedding_vectors]

        # Convert metadata to Mappings and extract IDs
        metadatas: Metadatas = []
        ids: list[str] = []
        for metadata in metadata_dicts:
            md = dict(metadata)
            if "id" not in md:
                raise ValueError("Metadata must contain 'id' field")
            ids.append(str(md["id"]))
            metadatas.append(cast(Mapping[str, Union[str, int, float, bool]], md))

        # Add embeddings to collection
        self.collection.add(embeddings=embeddings, metadatas=metadatas, ids=ids)
        logger.info("Added %d embeddings to vector store", len(embeddings))

    def query(
        self,
        query_vector: NDArray[np.float32],
        n_results: int = 5,
        where: Where | None = None,
    ) -> list[dict[str, Any]]:
        """Query the vector store.

        Args:
            query_vector: Query vector
            n_results: Number of results to return
            where: Optional filter conditions

        Returns:
            List of results with metadata

        Raises:
            ValueError: If query vector has wrong dimensions
        """
        # Check query vector dimensions
        if query_vector.shape != (384,):
            raise ValueError("Query vector must have 384 dimensions")

        # Convert query vector to list
        query_embedding: Sequence[float] = query_vector.tolist()

        # Query collection
        results = self.collection.query(
            query_embeddings=[query_embedding], n_results=n_results, where=where
        )

        # Extract metadata from results
        metadata_list = []
        metadatas = cast(list[list[dict[str, Any]]], results.get("metadatas"))
        if metadatas and metadatas[0]:
            ids = cast(list[list[str]], results["ids"])
            distances = cast(list[list[float]], results["distances"])
            for i in range(len(metadatas[0])):
                metadata = dict(metadatas[0][i])
                result = {
                    "id": metadata.get("id", ids[0][i]),  # Use stored ID if available
                    "distance": float(distances[0][i]),
                    "metadata": metadata,  # Include original metadata
                }
                metadata_list.append(result)

        return metadata_list

    def get_metadata(self) -> dict[str, Any]:
        """Get vector store metadata.

        Returns:
            Dictionary containing vector store metadata
        """
        # Get total vectors
        results = self.collection.get()
        total_vectors = len(results["ids"]) if results["ids"] else 0

        return {
            "id": "vector_store",
            "name": "Vector Store",
            "version": "1.0.0",
            "modified": time.time(),
            "total_vectors": total_vectors,
            "store_dir": str(self._store_dir),
        }

    def cleanup(self) -> None:
        """Clean up resources."""
        self._batch_queue.clear()
        self._embedding_cache.clear()
        self._model = None
        self.client.reset()

    async def get_stats(self) -> VectorStoreStats:
        """Get statistics about the vector store.

        Returns:
            VectorStoreStats: Statistics about the vector store
        """
        collection = self.client.get_collection("nova")
        count = collection.count()
        metadata = collection.get()

        return VectorStoreStats(
            collection_name="nova",
            num_embeddings=count,
            metadata=metadata
        )
