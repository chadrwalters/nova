import numpy as np
import pytest
from unittest.mock import Mock, patch

from nova.processing.types import Chunk, SearchResult
from nova.processing.vector_store import VectorStore, EphemeralVectorStore
from nova.rag.orchestrator import RAGOrchestrator, QueryResult


def test_rag_orchestrator_basic():
    # Create mock stores and embedding service
    vector_store = Mock(spec=VectorStore)
    embedding_service = Mock()
    
    # Set up mock returns
    embedding_service.embed_text.return_value = np.array([1, 0, 0, 0])
    vector_store.search.return_value = [
        SearchResult(
            chunk=Chunk(
                content="Test content 1",
                chunk_id="1",
                source="test1.md",
                embedding=np.array([1, 0, 0, 0])
            ),
            score=0.1,
            metadata={"key1": "value1"}
        )
    ]
    
    # Create orchestrator
    orchestrator = RAGOrchestrator(
        vector_store=vector_store,
        embedding_service=embedding_service
    )
    
    # Process query
    result = orchestrator.process_query("test query")
    
    # Verify embedding was generated
    embedding_service.embed_text.assert_called_once_with("test query")
    
    # Verify stores were searched
    vector_store.search.assert_called_once()
    
    # Verify result structure
    assert isinstance(result, QueryResult)
    assert "Test content 1" in result.context
    assert "test1.md" in result.sources
    assert result.metadata["key1"] == "value1"


def test_rag_orchestrator_with_ephemeral():
    # Create mock stores and embedding service
    vector_store = Mock(spec=VectorStore)
    ephemeral_store = Mock(spec=EphemeralVectorStore)
    embedding_service = Mock()
    
    # Set up mock returns
    embedding_service.embed_text.return_value = np.array([1, 0, 0, 0])
    vector_store.search.return_value = [
        SearchResult(
            chunk=Chunk(
                content="Persistent content",
                chunk_id="1",
                source="persistent.md",
                embedding=np.array([1, 0, 0, 0])
            ),
            score=0.2,
            metadata={"type": "persistent"}
        )
    ]
    ephemeral_store.search.return_value = [
        SearchResult(
            chunk=Chunk(
                content="Ephemeral content",
                chunk_id="2",
                source="ephemeral.md",
                embedding=np.array([0, 1, 0, 0]),
                is_ephemeral=True,
                expiration=9999999999
            ),
            score=0.1,
            metadata={"type": "ephemeral"}
        )
    ]
    
    # Create orchestrator
    orchestrator = RAGOrchestrator(
        vector_store=vector_store,
        ephemeral_store=ephemeral_store,
        embedding_service=embedding_service,
        top_k=2
    )
    
    # Process query
    result = orchestrator.process_query("test query")
    
    # Verify both stores were searched
    vector_store.search.assert_called_once()
    ephemeral_store.search.assert_called_once()
    
    # Verify results were merged and sorted
    assert "Ephemeral content" in result.context
    assert "Persistent content" in result.context
    assert "ephemeral.md" in result.sources
    assert "persistent.md" in result.sources
    assert result.metadata["type"] == "ephemeral"  # Last result's metadata


def test_rag_orchestrator_empty_results():
    # Create mock stores and embedding service
    vector_store = Mock(spec=VectorStore)
    embedding_service = Mock()
    
    # Set up mock returns
    embedding_service.embed_text.return_value = np.array([1, 0, 0, 0])
    vector_store.search.return_value = []
    
    # Create orchestrator
    orchestrator = RAGOrchestrator(
        vector_store=vector_store,
        embedding_service=embedding_service
    )
    
    # Process query
    result = orchestrator.process_query("test query")
    
    # Verify empty results handled gracefully
    assert result.context == ""
    assert result.sources == []
    assert result.metadata == {} 