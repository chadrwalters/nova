from dataclasses import dataclass
from typing import List, Optional

import numpy as np

from nova.processing.embedding import EmbeddingService
from nova.processing.types import SearchResult
from nova.processing.vector_store import VectorStore, EphemeralVectorStore


@dataclass
class QueryResult:
    context: str
    sources: List[str]
    metadata: dict


class RAGOrchestrator:
    def __init__(
        self,
        vector_store: VectorStore,
        ephemeral_store: Optional[EphemeralVectorStore] = None,
        embedding_service: Optional[EmbeddingService] = None,
        top_k: int = 5
    ):
        self.vector_store = vector_store
        self.ephemeral_store = ephemeral_store
        self.embedding_service = embedding_service or EmbeddingService()
        self.top_k = top_k

    def process_query(self, query: str) -> QueryResult:
        # Generate query embedding
        query_embedding = self.embedding_service.embed_text(query)

        # Search both stores
        results = self.vector_store.search(query_embedding, k=self.top_k)
        if self.ephemeral_store:
            ephemeral_results = self.ephemeral_store.search(query_embedding, k=self.top_k)
            results.extend(ephemeral_results)

        # Sort by score and take top k
        results.sort(key=lambda x: x.score)
        results = results[:self.top_k]

        # Build context
        context = self._build_context(results)
        sources = self._get_sources(results)
        
        # Prioritize ephemeral metadata by processing ephemeral results last
        metadata = {}
        persistent_results = [r for r in results if not r.chunk.is_ephemeral]
        ephemeral_results = [r for r in results if r.chunk.is_ephemeral]
        
        for result in persistent_results + ephemeral_results:
            metadata.update(result.metadata)

        return QueryResult(
            context=context,
            sources=sources,
            metadata=metadata
        )

    def _build_context(self, results: List[SearchResult]) -> str:
        """Build context from search results."""
        context_parts = []
        for result in results:
            chunk = result.chunk
            context_parts.append(f"[Source: {chunk.source}]\n{chunk.content}")
        return "\n\n".join(context_parts)

    def _get_sources(self, results: List[SearchResult]) -> List[str]:
        """Get unique sources from results."""
        return sorted(set(r.chunk.source for r in results))

    def _collect_metadata(self, results: List[SearchResult]) -> dict:
        """Collect metadata from results."""
        metadata = {}
        for result in results:
            metadata.update(result.metadata)
        return metadata 