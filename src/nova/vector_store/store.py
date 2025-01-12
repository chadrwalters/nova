"""Vector store implementation using Chroma."""

import logging
from pathlib import Path
from typing import Any, cast
from collections.abc import Mapping, Sequence

import chromadb
import numpy as np
from chromadb.api.types import Where
from numpy.typing import NDArray


logger = logging.getLogger(__name__)


class VectorStore:
    """Vector store for embeddings."""

    def __init__(self, store_dir: Path) -> None:
        """Initialize the vector store.

        Args:
            store_dir: Directory to store vectors in
        """
        self.store_dir = store_dir
        self.store_dir.mkdir(parents=True, exist_ok=True)

        # Initialize Chroma client
        self.client = chromadb.PersistentClient(path=str(store_dir))
        self.collection = self.client.get_or_create_collection("nova")

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
        embeddings: list[Sequence[float]] = [
            vector.tolist() for vector in embedding_vectors
        ]

        # Convert metadata to Mappings
        metadatas: list[Mapping[str, str | int | float | bool]] = [
            dict(m) for m in metadata_dicts
        ]

        # Generate IDs for embeddings
        ids = [f"vec_{i}" for i in range(len(embeddings))]

        # Add embeddings to collection
        self.collection.add(embeddings=embeddings, metadatas=metadatas, ids=ids)

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
        """
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
                metadata["id"] = ids[0][i]
                metadata["distance"] = float(distances[0][i])
                metadata_list.append(metadata)

        return metadata_list
