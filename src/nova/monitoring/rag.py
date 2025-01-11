"""RAG monitoring integration."""

import time
from typing import AsyncGenerator, Any, List
from dataclasses import dataclass

from .metrics import (
    QUERY_LATENCY,
    EMBEDDING_GENERATION_TIME,
    EMBEDDING_BATCH_SIZE,
    VECTOR_SEARCH_LATENCY
)
from .alerts import AlertManager


@dataclass
class RAGMetrics:
    """RAG performance metrics."""
    query_latency: float
    embedding_time: float
    search_time: float
    num_chunks: int
    num_context_blocks: int


class MonitoredRAGOrchestrator:
    """RAG orchestrator with monitoring support."""

    def __init__(self, orchestrator: Any, alert_manager: AlertManager):
        self.orchestrator = orchestrator
        self.alert_manager = alert_manager

    async def process_query(
        self,
        query: str,
    ) -> str:
        """Process query with monitoring."""
        start_time = time.time()
        metrics = RAGMetrics(
            query_latency=0.0,
            embedding_time=0.0,
            search_time=0.0,
            num_chunks=0,
            num_context_blocks=0
        )
        
        try:
            # Generate query embedding
            embed_start = time.time()
            query_embedding = await self._generate_embedding(query)
            metrics.embedding_time = time.time() - embed_start
            
            # Search for relevant chunks
            search_start = time.time()
            chunks = await self._search_chunks(query_embedding)
            metrics.search_time = time.time() - search_start
            metrics.num_chunks = len(chunks)
            
            # Create context blocks
            context_blocks = self._create_context_blocks(chunks)
            metrics.num_context_blocks = len(context_blocks)
            
            # Process with LLM
            response = await self.orchestrator.process_query(
                query,
                context_blocks=context_blocks
            )
            return response
                
        finally:
            # Update metrics
            metrics.query_latency = time.time() - start_time
            self._update_metrics(metrics)

    async def process_query_stream(
        self,
        query: str,
    ) -> AsyncGenerator[str, None]:
        """Process query with monitoring and streaming."""
        start_time = time.time()
        metrics = RAGMetrics(
            query_latency=0.0,
            embedding_time=0.0,
            search_time=0.0,
            num_chunks=0,
            num_context_blocks=0
        )
        
        try:
            # Generate query embedding
            embed_start = time.time()
            query_embedding = await self._generate_embedding(query)
            metrics.embedding_time = time.time() - embed_start
            
            # Search for relevant chunks
            search_start = time.time()
            chunks = await self._search_chunks(query_embedding)
            metrics.search_time = time.time() - search_start
            metrics.num_chunks = len(chunks)
            
            # Create context blocks
            context_blocks = self._create_context_blocks(chunks)
            metrics.num_context_blocks = len(context_blocks)
            
            # Process with LLM
            stream = await self.orchestrator.process_query_streaming(
                query,
                context_blocks=context_blocks
            )
            async for chunk in stream:
                yield chunk
                
        finally:
            # Update metrics
            metrics.query_latency = time.time() - start_time
            self._update_metrics(metrics)

    async def _generate_embedding(self, text: str) -> Any:
        """Generate embedding with monitoring."""
        with EMBEDDING_GENERATION_TIME.labels(
            model=self.orchestrator.embedding_service.model_name
        ).time():
            embedding = await self.orchestrator.embedding_service.embed_text(text)
            EMBEDDING_BATCH_SIZE.labels(model=self.orchestrator.embedding_service.model_name).set(1)  # Single text embedding
            return embedding

    async def _search_chunks(self, query_embedding: Any) -> List[Any]:
        """Search for relevant chunks with monitoring."""
        with VECTOR_SEARCH_LATENCY.labels(store_type="faiss").time():
            return await self.orchestrator.vector_store.search(
                query_embedding,
                k=self.orchestrator.top_k
            )

    def _create_context_blocks(self, chunks: List[Any]) -> List[Any]:
        """Create context blocks from chunks."""
        return self.orchestrator.create_context_blocks(chunks)

    def _update_metrics(self, metrics: RAGMetrics) -> None:
        """Update metrics after query processing."""
        # Update query latency
        QUERY_LATENCY.labels(query_type="rag").observe(metrics.query_latency)
        
        # Check alerts
        self.alert_manager.check_query_latency(metrics.query_latency)
        
        # Log detailed metrics
        self.orchestrator.logger.debug(
            "RAG metrics - "
            f"total_time={metrics.query_latency:.3f}s, "
            f"embedding_time={metrics.embedding_time:.3f}s, "
            f"search_time={metrics.search_time:.3f}s, "
            f"chunks={metrics.num_chunks}, "
            f"context_blocks={metrics.num_context_blocks}"
        )