"""Vector store resource handler implementation."""

import json
import logging
from pathlib import Path
from typing import Any, TypedDict, cast
from collections.abc import Callable

import numpy as np
from jsonschema.validators import validate
from chromadb.api.types import Embeddings, Metadatas

from nova.server.types import (
    ResourceError,
    ResourceHandler,
    ResourceMetadata,
    ResourceType,
)
from nova.vector_store.store import VectorStore

logger = logging.getLogger(__name__)


class VectorStoreAttributes(TypedDict):
    """Vector store attributes type."""

    collection_name: str
    embedding_dimension: int
    total_vectors: int
    index_type: str


class VectorStoreMetadata(TypedDict):
    """Vector store metadata type."""

    id: str
    type: str
    name: str
    version: str
    modified: float
    attributes: VectorStoreAttributes


class VectorStoreHandler(ResourceHandler):
    """Handler for vector store resource."""

    SCHEMA_PATH = (
        Path(__file__).parent.parent / "schemas" / "vector_store_resource.json"
    )
    EMBEDDING_DIMENSION = 384
    COLLECTION_NAME = "nova"
    INDEX_TYPE = "HNSW"
    VERSION = "1.0.0"
    RESOURCE_ID = "vector-store"

    def __init__(self, vector_store: VectorStore) -> None:
        """Initialize vector store handler.

        Args:
            vector_store: Vector store instance to manage
        """
        self._store = vector_store
        self._change_callbacks: list[Callable[[], None]] = []

        # Load schema
        with open(self.SCHEMA_PATH) as f:
            self._schema = json.load(f)

    def get_metadata(self) -> ResourceMetadata:
        """Get resource metadata.

        Returns:
            Dictionary containing resource metadata
        """
        store_metadata = self._store.get_metadata()
        metadata: VectorStoreMetadata = {
            "id": self.RESOURCE_ID,
            "type": ResourceType.VECTOR_STORE.name,
            "name": str(store_metadata["name"]),
            "version": self.VERSION,
            "modified": float(store_metadata["modified"]),
            "attributes": {
                "collection_name": self.COLLECTION_NAME,
                "embedding_dimension": self.EMBEDDING_DIMENSION,
                "total_vectors": int(store_metadata["total_vectors"]),
                "index_type": self.INDEX_TYPE,
            },
        }

        # Validate against schema
        validate(instance=metadata, schema=self._schema)
        return cast(ResourceMetadata, metadata)

    def validate_access(self, operation: str) -> bool:
        """Validate access for operation.

        Args:
            operation: Operation to validate ("read", "write", "delete")

        Returns:
            True if operation is allowed, False otherwise
        """
        return operation in ["read", "write", "delete"]

    def add_vectors(
        self,
        ids: list[str],
        embeddings: list[list[float]],
        metadatas: list[dict[str, Any]] | None = None,
    ) -> None:
        """Add vectors to store.

        Args:
            ids: List of vector IDs
            embeddings: List of vector embeddings
            metadatas: Optional list of metadata dictionaries

        Raises:
            ResourceError: If adding vectors fails or validation fails
        """
        try:
            # Validate inputs
            if not ids or not embeddings:
                raise ValueError("Empty ids or embeddings list")
            if len(ids) != len(embeddings):
                raise ValueError("Mismatched number of ids and embeddings")
            if metadatas and len(metadatas) != len(ids):
                raise ValueError("Mismatched number of metadatas")

            # Validate embedding dimensions
            for i, emb in enumerate(embeddings):
                if len(emb) != self.EMBEDDING_DIMENSION:
                    raise ValueError(
                        f"Invalid embedding dimension for vector {i}: expected {self.EMBEDDING_DIMENSION}, got {len(emb)}"
                    )

            # Convert embeddings directly to numpy arrays for chromadb
            embedding_vectors: Embeddings = [
                np.array(emb, dtype=np.float32) for emb in embeddings
            ]

            # Convert metadata to required format
            metadata_dicts: Metadatas = []
            if metadatas:
                for i, md in enumerate(metadatas):
                    if md is None:
                        md = {}
                    # Ensure all values are of supported types
                    filtered_md = {
                        k: v
                        for k, v in md.items()
                        if isinstance(v, (str, int, float, bool))
                    }
                    filtered_md["id"] = ids[i]  # Ensure ID is always present
                    metadata_dicts.append(filtered_md)
            else:
                metadata_dicts = [{"id": id_} for id_ in ids]

            # Add vectors to store
            self._store.collection.add(
                embeddings=embedding_vectors, metadatas=metadata_dicts, ids=ids
            )
            self._notify_change()
        except Exception as e:
            raise ResourceError(f"Failed to add vectors: {str(e)}")

    def query_vectors(
        self,
        query_embeddings: list[list[float]],
        n_results: int = 10,
        min_score: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Query vectors from store.

        Args:
            query_embeddings: List of query vector embeddings
            n_results: Maximum number of results to return
            min_score: Minimum similarity score threshold

        Returns:
            List of results with scores and metadata

        Raises:
            ResourceError: If querying vectors fails or validation fails
        """
        try:
            # Validate inputs
            if not query_embeddings:
                raise ValueError("Empty query embeddings list")
            if len(query_embeddings[0]) != self.EMBEDDING_DIMENSION:
                raise ValueError(
                    f"Invalid query dimension: expected {self.EMBEDDING_DIMENSION}, got {len(query_embeddings[0])}"
                )
            if n_results < 1:
                raise ValueError("n_results must be positive")
            if not 0.0 <= min_score <= 1.0:
                raise ValueError("min_score must be between 0 and 1")

            # Convert query embeddings to numpy array
            query_vector = np.array(query_embeddings[0], dtype=np.float32)

            # Query the store
            results = self._store.query(query_vector, n_results=n_results)

            # Convert distances to scores and filter by min_score
            filtered_results = []
            for result in results:
                score = 1.0 - result["distance"]  # Convert distance to similarity
                if score >= min_score:
                    result["score"] = score
                    filtered_results.append(result)

            return filtered_results
        except Exception as e:
            raise ResourceError(f"Failed to query vectors: {str(e)}")

    def delete_vectors(self, ids: list[str]) -> None:
        """Delete vectors from store.

        Args:
            ids: List of vector IDs to delete

        Raises:
            ResourceError: If deleting vectors fails or validation fails
        """
        try:
            # Validate inputs
            if not ids:
                raise ValueError("Empty ids list")

            # Delete vectors from store
            self._store.collection.delete(ids=ids)
            self._notify_change()
        except Exception as e:
            raise ResourceError(f"Failed to delete vectors: {str(e)}")

    def on_change(self, callback: Callable[[], None]) -> None:
        """Register change callback.

        Args:
            callback: Function to call when store changes
        """
        if not callable(callback):
            raise ValueError("Callback must be callable")
        self._change_callbacks.append(callback)

    def _notify_change(self) -> None:
        """Notify registered callbacks of change."""
        for callback in self._change_callbacks:
            try:
                callback()
            except Exception as e:
                logger.error(f"Error in change callback: {e}")

    def cleanup(self) -> None:
        """Clean up resources."""
        self._change_callbacks.clear()
        self._store.cleanup()
