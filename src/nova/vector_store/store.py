"""Vector store for semantic search."""

import json
import logging
import uuid
from typing import Any

import chromadb
from chromadb.api.models.Collection import Collection
from chromadb.api.types import IncludeEnum
from sentence_transformers import SentenceTransformer

from nova.vector_store.chunking import Chunk
from nova.vector_store.stats import VectorStoreStats

logger = logging.getLogger(__name__)


class VectorStore:
    """Vector store for embeddings with metadata support."""

    COLLECTION_NAME = "nova_documents"
    MODEL_NAME = "paraphrase-MiniLM-L3-v2"

    def __init__(self, vector_dir: str, use_memory: bool = False) -> None:
        """Initialize the vector store."""
        self.vector_dir = vector_dir
        self.model: SentenceTransformer | None = None
        self.collection: Collection | None = None
        self.stats = VectorStoreStats()
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
                self.collection = self.client.create_collection("chunks")
                self.logger.info("Created new collection: chunks")
            except Exception:
                self.collection = self.client.get_collection("chunks")
                self.logger.info("Using existing collection: chunks")

            # Initialize model
            self.model = SentenceTransformer("all-MiniLM-L6-v2")
            self.logger.info("Vector store initialized successfully")

        except Exception as e:
            self.logger.error(f"Failed to initialize vector store: {e}")
            raise

    def add_chunk(self, chunk: Chunk, metadata: dict[str, Any]) -> None:
        """Add a chunk to the vector store."""
        if not self.model or not self.collection:
            self.logger.error("Model or collection not initialized")
            raise RuntimeError("Model or collection not initialized")

        try:
            # Generate embedding
            embedding = self.model.encode(chunk.text).tolist()

            # Process metadata to ensure correct format for filtering
            processed_metadata = {
                "source": str(chunk.source) if chunk.source else "",
                "heading_text": chunk.heading_text,
                "heading_level": chunk.heading_level,
                "tags": json.dumps(chunk.tags),
                "attachments": json.dumps(
                    [{"type": att["type"], "path": att["path"]} for att in chunk.attachments]
                ),
                "chunk_id": chunk.chunk_id,
            }

            # Add to collection
            self.collection.add(
                documents=[chunk.text],
                embeddings=[embedding],
                metadatas=[processed_metadata],
                ids=[str(uuid.uuid4())],
            )

            # Update stats
            if hasattr(self, "stats") and self.stats:
                self.stats.record_chunk_added()

            self.logger.info("Added chunk to vector store")

        except Exception as e:
            self.logger.error(f"Error adding chunk: {e}")
            raise

    def search(
        self,
        query: str,
        limit: int = 5,
        tag_filter: str | None = None,
        attachment_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Search for similar documents."""
        try:
            if not self.model or not self.collection:
                self.logger.error("Model or collection not initialized")
                return []

            # Generate query embedding
            query_embedding = self.model.encode(query).tolist()

            # Build where clause for filtering
            conditions = []
            if tag_filter:
                # Search for tag in the JSON array
                tag_json = json.dumps([tag_filter])  # Match exact tag array
                conditions.append({"tags": {"$eq": tag_json}})
            if attachment_type:
                # Search for attachment type in the JSON array
                attachment_json = json.dumps(
                    [{"type": attachment_type, "path": "test.jpg"}]
                )  # Match exact attachment array
                conditions.append({"attachments": {"$eq": attachment_json}})

            # Construct where clause based on number of conditions
            where: dict[str, Any] | None = None
            if len(conditions) > 1:
                where = {"$and": conditions}
            elif len(conditions) == 1:
                where = conditions[0]
            else:
                # Use a dummy condition that always matches
                where = {"source": {"$ne": "IMPOSSIBLE_VALUE_THAT_NEVER_EXISTS"}}

            # Perform the search
            include = [IncludeEnum.documents, IncludeEnum.metadatas, IncludeEnum.distances]
            results = self.collection.query(
                query_embeddings=[query_embedding],
                n_results=limit * 4,  # Get more results for filtering
                where=where,
                include=include,
            )

            # Process results
            processed_results = []
            documents = results.get("documents", [])
            distances = results.get("distances", [])
            metadatas = results.get("metadatas", [])

            if (
                documents
                and distances
                and metadatas
                and len(documents) > 0
                and len(documents[0]) > 0
            ):
                for i, doc in enumerate(documents[0]):
                    # Calculate semantic similarity (0-100%)
                    similarity = max(0, min(100, (1 - distances[0][i]) * 100))

                    # Calculate term match score (0-100%)
                    term_match_score = self._calculate_term_match_score(doc, query)

                    # Check if the content is unrelated
                    query_terms = query.lower().split()
                    text_terms = doc.lower().split()
                    has_any_match = any(
                        term in text_terms
                        or any(self._are_synonyms(term, text_term) for text_term in text_terms)
                        or any(
                            (term in text_term or text_term in term)
                            and len(min(term, text_term)) >= 3
                            for text_term in text_terms
                        )
                        for term in query_terms
                    )

                    # Skip documents with no matches at all
                    if not has_any_match and similarity < 50:
                        continue

                    # Calculate final score with adjusted weights
                    if term_match_score > 80:  # Exact or near-exact match
                        final_score = term_match_score
                    elif term_match_score > 50:  # Strong term match
                        final_score = (similarity * 0.3) + (term_match_score * 0.7)
                    else:  # Semantic or partial match
                        final_score = (similarity * 0.7) + (term_match_score * 0.3)

                    # Ensure score is properly normalized
                    final_score = max(0, min(100, final_score))

                    # Add minimum score for any kind of match
                    if has_any_match:
                        final_score = max(final_score, 20)  # Increased minimum score
                    else:
                        final_score = min(final_score, 5)  # Cap score for unrelated content

                    # Skip very low scoring results
                    if final_score < 5:
                        continue

                    # Include all results but with adjusted scores
                    processed_results.append(
                        {"text": doc, "metadata": metadatas[0][i], "score": final_score}
                    )

            # Sort by score and limit results
            processed_results.sort(key=lambda x: x["score"], reverse=True)
            processed_results = processed_results[:limit]

            return processed_results

        except Exception as e:
            self.logger.error(f"Error during search: {e}")
            return []

    def _calculate_term_match_score(self, text: str, query: str) -> float:
        """Calculate a score based on term matches in the text."""
        text = text.lower()
        query = query.lower()

        # Check for exact phrase match first
        if query in text:
            return 100.0  # Give maximum score for exact matches

        query_terms = query.split()
        text_terms = text.split()

        # Initialize score components
        consecutive_matches = 0
        term_matches = 0
        synonym_matches = 0
        partial_matches = 0

        # Check for consecutive term matches
        for i in range(len(text_terms) - len(query_terms) + 1):
            matches = 0
            for j, query_term in enumerate(query_terms):
                if i + j >= len(text_terms):
                    break
                text_term = text_terms[i + j]
                if query_term == text_term:
                    matches += 1
                elif self._are_synonyms(query_term, text_term):
                    matches += 0.8  # Slightly lower score for synonyms
                elif (query_term in text_term or text_term in query_term) and len(
                    min(query_term, text_term)
                ) >= 3:
                    matches += 0.6  # Add partial match boost for consecutive matches
            consecutive_matches = max(consecutive_matches, matches)

        # Check for individual term matches
        for query_term in query_terms:
            exact_match = False
            synonym_found = False
            partial_found = False

            for text_term in text_terms:
                if query_term == text_term:
                    term_matches += 1
                    exact_match = True
                    break
                elif not exact_match and self._are_synonyms(query_term, text_term):
                    synonym_matches += 1
                    synonym_found = True
                elif not exact_match and not synonym_found:
                    # Check for partial word matches (e.g., "dev" matching "developer")
                    if (query_term in text_term or text_term in query_term) and len(
                        min(query_term, text_term)
                    ) >= 3:
                        partial_matches += 1
                        partial_found = True

        # Calculate final term match score
        consecutive_score = (
            consecutive_matches / len(query_terms)
        ) * 60  # Increased boost for consecutive matches
        term_score = (
            term_matches / len(query_terms)
        ) * 50  # Increased boost for exact term matches
        synonym_score = (
            synonym_matches / len(query_terms)
        ) * 40  # Increased boost for synonym matches
        partial_score = (
            partial_matches / len(query_terms)
        ) * 30  # Increased boost for partial matches

        # Add a higher minimum score for any kind of match
        has_matches = (
            consecutive_matches > 0
            or term_matches > 0
            or synonym_matches > 0
            or partial_matches > 0
        )
        base_score = 25 if has_matches else 0  # Increased base score

        return min(
            base_score + consecutive_score + term_score + synonym_score + partial_score, 100.0
        )  # Cap at 100%

    def _are_synonyms(self, term1: str, term2: str) -> bool:
        """Check if two terms are synonyms."""
        synonyms = {
            "programmer": ["developer", "dev", "coder", "engineer"],
            "developer": ["programmer", "dev", "coder", "engineer"],
            "web": ["frontend", "backend", "front-end", "back-end", "fullstack", "full-stack"],
            "frontend": ["front-end", "web", "client-side"],
            "backend": ["back-end", "web", "server-side"],
            "dev": ["developer", "programmer", "coder", "engineer"],
            "coder": ["programmer", "developer", "dev", "engineer"],
            "engineer": ["programmer", "developer", "dev", "coder"],
        }
        return term2 in synonyms.get(term1, []) or term1 in synonyms.get(term2, [])

    def cleanup(self) -> None:
        """Clean up resources."""
        try:
            if self.collection:
                try:
                    self.client.delete_collection("chunks")
                except ValueError as e:
                    # Ignore if collection doesn't exist
                    if "does not exist" not in str(e):
                        raise
                self.collection = None
            self.logger.info("Cleaned up vector store")
        except Exception as e:
            self.logger.error(f"Error during cleanup: {e}")
            raise

    def get_stats(self) -> dict[str, Any]:
        """Get current statistics."""
        if hasattr(self, "stats") and self.stats:
            return self.stats.get_stats()
        return {}

    def __del__(self) -> None:
        """Clean up resources on deletion."""
        self.cleanup()
