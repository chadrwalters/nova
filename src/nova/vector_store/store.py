"""Vector store implementation using Chroma."""
from dataclasses import dataclass
from typing import Any, cast
from collections.abc import Sequence
import chromadb
from chromadb.config import Settings
from chromadb.api.types import QueryResult, Embeddings, Metadatas, IncludeEnum
import numpy as np
import numpy.typing as npt

from .chunking import Chunk


@dataclass
class SearchResult:
    """Result from a vector store search."""

    chunk: Chunk
    score: float


class VectorStore:
    """Vector store for document chunks.

    Features:
    1. Persistent storage for long-term data
    2. Ephemeral storage for session-specific data
    3. Combined search across both stores
    4. Configurable distance metrics
    """

    def __init__(
        self,
        persistent_path: str,
        collection_name: str = "nova",
        distance_func: str = "cosine",
    ):
        """Initialize the vector store.

        Args:
            persistent_path: Path to store persistent data
            collection_name: Name of the collection
            distance_func: Distance function to use
        """
        self.collection_name = collection_name
        self.distance_func = distance_func

        # Initialize persistent client
        self.persistent_client = chromadb.PersistentClient(
            path=persistent_path,
            settings=Settings(anonymized_telemetry=False),
        )

        # Initialize ephemeral client
        self.ephemeral_client = chromadb.EphemeralClient(
            Settings(anonymized_telemetry=False)
        )

        # Create or get collections
        self.persistent_collection = self.persistent_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": distance_func},
        )

        self.ephemeral_collection = self.ephemeral_client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": distance_func},
        )

    def add_chunks(
        self,
        chunks: list[Chunk],
        embeddings: list[npt.NDArray[np.float32]],
        is_ephemeral: bool = False,
    ) -> None:
        """Add chunks to the vector store.

        Args:
            chunks: List of chunks to add
            embeddings: Corresponding embeddings
            is_ephemeral: Whether to add to ephemeral storage
        """
        # Convert chunks to IDs and metadata
        ids = [str(i) for i in range(len(chunks))]
        metadatas = [self._chunk_to_metadata(chunk) for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        embeddings_list = [cast(Sequence[float], e.tolist()) for e in embeddings]

        # Add to appropriate collection
        collection = (
            self.ephemeral_collection if is_ephemeral else self.persistent_collection
        )
        collection.add(
            ids=ids,
            embeddings=cast(Embeddings, embeddings_list),
            documents=documents,
            metadatas=cast(Metadatas, metadatas),
        )

    def search(
        self,
        query_embedding: npt.NDArray[np.float32],
        limit: int = 5,
        min_score: float = 0.0,
        include_ephemeral: bool = True,
    ) -> list[SearchResult]:
        """Search for similar chunks.

        Args:
            query_embedding: Query embedding
            limit: Maximum number of results
            min_score: Minimum similarity score
            include_ephemeral: Whether to include ephemeral results

        Returns:
            List of search results
        """
        results: list[SearchResult] = []

        # Search persistent collection
        persistent_results = self.persistent_collection.query(
            query_embeddings=cast(
                Embeddings, [cast(Sequence[float], query_embedding.tolist())]
            ),
            n_results=limit,
            include=[
                cast(IncludeEnum, "documents"),
                cast(IncludeEnum, "metadatas"),
                cast(IncludeEnum, "distances"),
            ],
        )
        results.extend(self._process_results(persistent_results))

        # Search ephemeral if requested
        if include_ephemeral:
            ephemeral_results = self.ephemeral_collection.query(
                query_embeddings=cast(
                    Embeddings, [cast(Sequence[float], query_embedding.tolist())]
                ),
                n_results=limit,
                include=[
                    cast(IncludeEnum, "documents"),
                    cast(IncludeEnum, "metadatas"),
                    cast(IncludeEnum, "distances"),
                ],
            )
            results.extend(self._process_results(ephemeral_results))

        # Sort by score and apply minimum score filter
        results = [r for r in results if r.score >= min_score]
        results.sort(key=lambda x: x.score, reverse=True)

        return results[:limit]

    def clear_ephemeral(self) -> None:
        """Clear all ephemeral data."""
        self.ephemeral_collection.delete(where={})

    def _process_results(self, results: QueryResult) -> list[SearchResult]:
        """Process raw query results into SearchResults.

        Args:
            results: Raw query results from Chroma

        Returns:
            List of processed search results
        """
        processed: list[SearchResult] = []

        if not results or not results["ids"]:
            return processed

        documents = cast(list[list[str]], results["documents"])[0]
        metadatas = cast(list[list[dict[str, Any]]], results["metadatas"])[0]
        distances = cast(list[list[float]], results["distances"])[0]

        for doc, meta, dist in zip(documents, metadatas, distances):
            chunk = self._metadata_to_chunk(doc, meta)
            # Convert distance to similarity score
            score = 1.0 - dist if self.distance_func == "cosine" else 1.0 / (1.0 + dist)
            processed.append(SearchResult(chunk=chunk, score=score))

        return processed

    def _chunk_to_metadata(self, chunk: Chunk) -> dict[str, Any]:
        """Convert chunk to metadata dictionary.

        Args:
            chunk: Chunk to convert

        Returns:
            Metadata dictionary
        """
        return {
            "source": chunk.source_location,
            "tags": ",".join(chunk.tags),
            "heading_context": ",".join(chunk.heading_context),
            "start_line": chunk.start_line,
            "end_line": chunk.end_line,
        }

    def _metadata_to_chunk(self, content: str, metadata: dict[str, Any]) -> Chunk:
        """Convert metadata back to chunk.

        Args:
            content: Chunk content
            metadata: Metadata dictionary

        Returns:
            Reconstructed chunk
        """
        return Chunk(
            content=content,
            source_location=str(metadata["source"]),
            tags=str(metadata["tags"]).split(",") if metadata["tags"] else [],
            heading_context=str(metadata["heading_context"]).split(",")
            if metadata["heading_context"]
            else [],
            start_line=int(metadata["start_line"]),
            end_line=int(metadata["end_line"]),
        )
