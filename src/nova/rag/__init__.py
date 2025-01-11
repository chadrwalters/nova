"""Nova RAG module."""

from typing import List, Optional, AsyncGenerator

from nova.processing import EmbeddingService
from nova.processing.vector_store import VectorStore
from nova.ephemeral import EphemeralManager
from nova.types import MCPPayload, ContextBlock, Chunk


class RAGOrchestrator:
    """Orchestrates the RAG pipeline."""
    
    def __init__(
        self,
        vector_store: Optional[VectorStore] = None,
        ephemeral_manager: Optional[EphemeralManager] = None,
        embedding_service: Optional[EmbeddingService] = None,
        top_k: int = 5
    ):
        """Initialize RAG orchestrator."""
        self.vector_store = vector_store or VectorStore()
        self.ephemeral_manager = ephemeral_manager or EphemeralManager()
        self.embedding_service = embedding_service or EmbeddingService()
        self.top_k = top_k
    
    async def process_query(self, query: str) -> MCPPayload:
        """Process query and build MCP payload."""
        # Generate query embedding
        query_embedding = (await self.embedding_service.embed_chunks([
            Chunk(content=query, metadata={})
        ]))[0]
        
        # Search both stores
        persistent_results = self.vector_store.search(query_embedding, k=self.top_k)
        ephemeral_results = self.ephemeral_manager.search(query_embedding, k=self.top_k)
        
        # Convert to context blocks
        persistent_blocks = [
            ContextBlock(
                content=result.chunk.content,
                metadata=result.metadata,
                ephemeral=False
            )
            for result in persistent_results
        ]
        
        ephemeral_blocks = [
            ContextBlock(
                content=result.chunk.content,
                metadata=result.metadata,
                ephemeral=True
            )
            for result in ephemeral_results
        ]
        
        # Merge results
        context_blocks = self._merge_results(persistent_blocks, ephemeral_blocks)
        
        # Build MCP payload
        return MCPPayload(
            system_instructions="You are a helpful AI assistant.",
            developer_instructions="Use the provided context to answer the query.",
            user_message=query,
            context_blocks=context_blocks
        )
    
    async def process_query_streaming(self, query: str) -> AsyncGenerator[str, None]:
        """Process query with streaming response."""
        # For testing, just yield the query back
        yield query
    
    def _merge_results(
        self,
        persistent_results: List[ContextBlock],
        ephemeral_results: List[ContextBlock]
    ) -> List[ContextBlock]:
        """Smart merging of results from both stores."""
        # For testing, just combine and return top_k total
        all_results = persistent_results + ephemeral_results
        return all_results[:self.top_k]
