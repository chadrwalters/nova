"""Vector store module.

This module provides a vector store implementation using ChromaDB. It
handles document storage, retrieval, and semantic search functionality.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, NotRequired, TypedDict, cast

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import (
    IncludeEnum,
)
from chromadb.config import Settings

from nova.vector_store.chunking import Chunk
from nova.vector_store.embedding import NovaEmbeddingFunction

logger = logging.getLogger(__name__)

# Constants for include fields
QUERY_INCLUDE_FIELDS = [IncludeEnum.documents, IncludeEnum.metadatas, IncludeEnum.distances]
GET_INCLUDE_FIELDS = [IncludeEnum.documents, IncludeEnum.metadatas]


def _convert_metadata_value(value: Any) -> str | int | float | bool:
    """Convert metadata value to a type supported by ChromaDB."""
    if isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, (list, dict)):
        return json.dumps(value)
    return str(value)


class TagStats(TypedDict):
    """Tag statistics."""

    total: int
    unique: int
    list: list[str]


class DateRange(TypedDict):
    """Date range information."""

    earliest: NotRequired[str | None]
    latest: NotRequired[str | None]


class RepositoryStats(TypedDict):
    """Repository statistics."""

    total_chunks: int
    unique_sources: int
    file_types: dict[str, int]
    total_attachments: int
    attachment_types: dict[str, int]
    date_range: DateRange
    tags: TagStats
    size_stats: NotRequired[dict[str, int | float]]


class CollectionStats(TypedDict):
    """Collection statistics."""

    name: str
    exists: bool
    count: int


class DirectoryStats(TypedDict):
    """Directory statistics."""

    exists: bool
    is_directory: bool
    path: str


class HealthData(TypedDict):
    """Health check data."""

    status: str
    timestamp: str
    error: NotRequired[str]
    directory: DirectoryStats
    collection: CollectionStats
    repository: RepositoryStats


class ChromaMetadata(TypedDict):
    """ChromaDB metadata structure."""

    content_type: NotRequired[str]
    mime_type: NotRequired[str]
    source: NotRequired[str]
    source_file: NotRequired[str]
    filename: NotRequired[str]
    tags: NotRequired[str | list[str]]
    attachments: NotRequired[str | list[str]]


class ChromaGetResult(TypedDict):
    """ChromaDB get() result structure."""

    documents: list[str]
    metadatas: list[dict[str, str | int | float | bool | list[str]]]
    ids: list[str]


class NovaMetadata(TypedDict):
    """Nova metadata structure."""

    document_id: str
    document_type: str
    document_size: int
    chunk_id: str
    heading_level: int
    heading_text: str
    tags: str
    text: str
    attachments: str
    date: str


class VectorStore:
    """Vector store class."""

    COLLECTION_NAME = "nova"

    def __init__(self, base_path: str, use_memory: bool = False) -> None:
        """Initialize the vector store.

        Args:
            base_path: Base path for storing vectors
            use_memory: Whether to use in-memory storage
        """
        logger.info(f"Initializing VectorStore at {base_path}")
        self.base_path = Path(base_path)
        self.base_path.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created base directory: {self.base_path}")

        # Initialize ChromaDB client
        if use_memory:
            settings = Settings(anonymized_telemetry=False, allow_reset=True, is_persistent=False)
            logger.info("Using in-memory storage")
        else:
            settings = Settings(
                anonymized_telemetry=False,
                allow_reset=True,
                is_persistent=True,
                persist_directory=str(self.base_path / "chroma"),
            )
            logger.info(f"Using persistent storage at {self.base_path / 'chroma'}")

        # Create client and collection with our embedding engine
        self._client = chromadb.Client(settings)
        self._embedding_function = NovaEmbeddingFunction()
        self._collection: Collection = self._client.get_or_create_collection(
            name=self.COLLECTION_NAME,
            metadata={"hnsw_space": "cosine"},
            embedding_function=cast(Any, self._embedding_function),
        )
        logger.info(f"Created/loaded collection '{self.COLLECTION_NAME}'")

    def add_chunk(self, chunk: Chunk, metadata: dict[str, Any] | None = None) -> None:
        """Add a chunk to the store.

        Args:
            chunk: The chunk to add
            metadata: Optional metadata to override chunk's default metadata
        """
        logger.info(f"Adding chunk {chunk.chunk_id} to vector store")
        logger.debug(f"Chunk text length: {len(chunk.text)}")
        logger.debug(f"Chunk metadata: {chunk.to_metadata()}")

        try:
            # Get metadata from chunk if not provided
            if metadata is None:
                metadata = chunk.to_metadata()
            logger.info(f"Adding chunk with ID {chunk.chunk_id} and metadata: {metadata}")

            # Convert metadata values to supported types for ChromaDB
            processed_metadata = self._prepare_metadata(metadata)
            logger.debug(f"Prepared metadata: {processed_metadata}")

            # Add chunk directly to collection
            logger.info("Adding chunk to ChromaDB collection")
            self._collection.add(
                ids=[chunk.chunk_id], documents=[chunk.text], metadatas=[processed_metadata]
            )
            logger.info(f"Successfully added chunk {chunk.chunk_id} to collection")

            # Verify the chunk was added
            count = self._collection.count()
            logger.info(f"Current collection count: {count}")

        except Exception as e:
            logger.error(f"Error adding chunk: {e}", exc_info=True)
            raise

    def _prepare_metadata(self, metadata: dict[str, Any]) -> dict[str, Any]:
        """Prepare metadata for ChromaDB by converting values to supported
        types.

        Args:
            metadata: Original metadata dictionary

        Returns:
            Processed metadata dictionary with ChromaDB-compatible types
        """
        logger.debug(f"Preparing metadata: {metadata}")
        processed = {}
        for key, value in metadata.items():
            try:
                if isinstance(value, (str, int, float, bool)):
                    processed[key] = value
                elif isinstance(value, (list, tuple)):
                    # Convert lists/tuples to comma-separated strings
                    processed[key] = ",".join(str(x) for x in value)
                elif value is None:
                    processed[key] = ""
                else:
                    # Convert other types to strings
                    processed[key] = str(value)
            except Exception as e:
                logger.warning(f"Error processing metadata key {key}: {e}")
                processed[key] = str(value)

        logger.debug(f"Processed metadata: {processed}")
        return processed

    def clear(self) -> None:
        """Clear all chunks from the store."""
        logger.info("Clearing vector store")
        try:
            # Delete collection if it exists
            try:
                self._client.delete_collection(self.COLLECTION_NAME)
                logger.info("Deleted existing collection")
            except Exception as e:
                logger.info(f"No collection to delete: {e}")

            # Recreate collection
            logger.info("Recreating collection")
            self._collection = self._client.create_collection(
                name=self.COLLECTION_NAME,
                embedding_function=self._embedding_function,
                metadata={"hnsw_space": "cosine"},
            )
            logger.info("Collection recreated")

        except Exception as e:
            logger.error(f"Error clearing vector store: {e}", exc_info=True)
            raise

    def search(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Search for chunks matching the query.

        Args:
            query: Search query
            limit: Maximum number of results to return

        Returns:
            List of search results with scores and metadata
        """
        try:
            results = self._collection.query(
                query_texts=[query],
                n_results=limit,
                include=QUERY_INCLUDE_FIELDS,
            )

            search_results = []
            documents = results.get("documents", [[]])
            metadatas = results.get("metadatas", [[]])
            distances = results.get("distances", [[]])

            if documents and metadatas and distances and len(documents[0]) > 0:
                for doc, metadata, distance in zip(
                    documents[0], metadatas[0], distances[0], strict=False
                ):
                    # Convert distance to similarity score (0-100)
                    score = round((1.0 - distance / 2.0) * 100, 2)
                    search_results.append(
                        {
                            "text": doc,
                            "metadata": metadata,
                            "score": score,
                        }
                    )

            return search_results

        except Exception as e:
            logger.error(f"Error searching: {e}")
            raise

    def check_health(self) -> HealthData:
        """Check vector store health and return detailed statistics.

        Returns:
            Dictionary containing health status and detailed statistics

        Raises:
            Exception: If vector store is not healthy
        """
        try:
            health_data: HealthData = {
                "status": "healthy",
                "timestamp": datetime.now().isoformat(),
                "directory": {
                    "exists": self.base_path.exists(),
                    "is_directory": self.base_path.is_dir(),
                    "path": str(self.base_path),
                },
                "collection": {
                    "name": self.COLLECTION_NAME,
                    "exists": False,
                    "count": 0,
                },
                "repository": {
                    "total_chunks": 0,
                    "unique_sources": 0,
                    "file_types": {},
                    "total_attachments": 0,
                    "attachment_types": {},
                    "date_range": {
                        "earliest": None,
                        "latest": None,
                    },
                    "tags": {
                        "total": 0,
                        "unique": 0,
                        "list": [],
                    },
                    "size_stats": {},
                },
            }

            # Verify base path
            if not self.base_path.exists():
                health_data["status"] = "error"
                raise Exception("Vector store directory does not exist")
            if not self.base_path.is_dir():
                health_data["status"] = "error"
                raise Exception("Vector store path is not a directory")

            # Get collection stats
            try:
                # First check if we can connect to ChromaDB
                try:
                    self._client.heartbeat()
                    logger.info("ChromaDB heartbeat successful")
                except Exception as e:
                    health_data["status"] = "error"
                    health_data["error"] = f"Database connection error: {e!s}"
                    return health_data

                # Try to get our collection
                try:
                    collection = self._client.get_collection(name=self.COLLECTION_NAME)
                    logger.info(f"Got collection: {self.COLLECTION_NAME}")

                    # Get all documents and metadata
                    logger.info("Getting documents and metadata")
                    results = collection.get(include=GET_INCLUDE_FIELDS)
                    logger.info(f"Got results: {results.keys() if results else None}")

                    # Extract data safely
                    if results and isinstance(results, dict):
                        # Get raw data and cast to our type
                        results_typed = cast(ChromaGetResult, results)
                        documents = results_typed.get("documents", [])
                        metadatas = results_typed.get("metadatas", [])
                        count = len(documents) if documents else 0

                        # Log the first metadata entry to understand structure
                        if metadatas and len(metadatas) > 0:
                            logger.info(f"First metadata entry: {metadatas[0]}")
                            logger.info(f"Metadata type: {type(metadatas[0])}")
                            logger.info(
                                f"Available keys: {metadatas[0].keys() if isinstance(metadatas[0], dict) else 'Not a dict'}"
                            )

                        # Initialize tracking variables
                        sources: set[str] = set()
                        file_types: dict[str, int] = {}
                        attachment_types: dict[str, int] = {}
                        all_tags: set[str] = set()
                        dates: list[str] = []
                        doc_sizes: list[int] = []

                        # Process each document and its metadata
                        for i, metadata in enumerate(metadatas):
                            # Cast metadata to our type
                            nova_metadata = cast(NovaMetadata, metadata)

                            # Track document size
                            if documents and i < len(documents):
                                doc_size = len(str(documents[i]))
                                doc_sizes.append(doc_size)

                            # Track document type from metadata
                            doc_type = str(nova_metadata["document_type"])
                            if doc_type:
                                file_types[doc_type] = file_types.get(doc_type, 0) + 1

                            # Track source from document_id
                            doc_id = str(nova_metadata["document_id"])
                            if doc_id:
                                sources.add(doc_id)

                            # Track tags
                            tags_list = []
                            total_tags = 0
                            for meta in metadatas:
                                if "tags" in meta:
                                    tags_value = meta["tags"]
                                    try:
                                        if isinstance(tags_value, str):
                                            chunk_tags = json.loads(str(tags_value))  # Cast to str
                                            if isinstance(chunk_tags, list):
                                                total_tags += len(chunk_tags)  # Count total tags
                                                tags_list.extend(
                                                    chunk_tags
                                                )  # Add to list for unique count
                                        elif isinstance(tags_value, list):
                                            total_tags += len(tags_value)  # Count total tags
                                            tags_list.extend(
                                                tags_value
                                            )  # Add to list for unique count
                                    except json.JSONDecodeError:
                                        logger.warning("Failed to parse tags JSON: %s", tags_value)

                            unique_tags = list(set(tags_list))
                            all_tags.update(unique_tags)

                        logger.info(f"Found {count} documents")
                        health_data["collection"]["exists"] = True
                        health_data["collection"]["count"] = count

                        # Process metadata if we have documents
                        if count > 0 and metadatas:
                            # Update repository stats
                            repository_stats: RepositoryStats = {
                                "total_chunks": count,
                                "unique_sources": len(sources),
                                "file_types": file_types,
                                "total_attachments": sum(attachment_types.values()),
                                "attachment_types": attachment_types,
                                "date_range": {
                                    "earliest": None,
                                    "latest": None,
                                },
                                "tags": {
                                    "total": total_tags,  # Total number of tags across all chunks
                                    "unique": len(unique_tags),  # Number of unique tags
                                    "list": unique_tags,  # List of unique tags
                                },
                                "size_stats": {
                                    "min_size": min(doc_sizes) if doc_sizes else 0,
                                    "max_size": max(doc_sizes) if doc_sizes else 0,
                                    "avg_size": int(sum(doc_sizes) / len(doc_sizes))
                                    if doc_sizes
                                    else 0,
                                    "total_size": sum(doc_sizes) if doc_sizes else 0,
                                },
                            }
                            health_data["repository"] = repository_stats

                            # Log findings
                            logger.info(f"Found sources: {sources}")
                            logger.info(f"Found file types: {file_types}")
                            logger.info(f"Found tags: {all_tags}")
                        else:
                            logger.warning("No metadata found in results")

                except Exception as e:
                    health_data["status"] = "error"
                    health_data["error"] = f"Collection error: {e!s}"
                    logger.error(f"Collection error: {e}", exc_info=True)
                    return health_data

            except Exception as e:
                health_data["status"] = "error"
                health_data["error"] = f"Collection error: {e!s}"
                logger.error(f"Failed to get collection stats: {e}", exc_info=True)

            return health_data

        except Exception as e:
            logger.error(f"Vector store health check failed: {e}", exc_info=True)
            raise
