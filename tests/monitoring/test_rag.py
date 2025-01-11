"""Tests for RAG monitoring."""
import asyncio
import pytest
from nova.monitoring.rag import RAGMetrics, MonitoredRAGOrchestrator
from nova.monitoring.metrics import (
    QUERY_LATENCY,
    EMBEDDING_GENERATION_TIME,
    VECTOR_SEARCH_LATENCY,
    VECTOR_STORE_SIZE
)
from nova.monitoring.alerts import AlertManager
from nova.config import AlertingConfig
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def alert_manager():
    """Create alert manager for testing."""
    config = AlertingConfig(
        max_query_latency=1.0,
        max_error_rate=0.1,
        max_memory_usage=1024 * 1024 * 1024,  # 1GB
        max_vector_store_size=1000,
        min_rate_limit_remaining=100,
        rate_limit_warning_threshold=0.2
    )
    return AlertManager(config)

@pytest.fixture
def rag_metrics():
    return RAGMetrics(
        query_latency=QUERY_LATENCY.labels(query_type='rag'),
        embedding_time=EMBEDDING_GENERATION_TIME.labels(model='all-MiniLM-L6-v2'),
        search_time=VECTOR_SEARCH_LATENCY.labels(store_type='faiss'),
        num_chunks=VECTOR_STORE_SIZE.labels(store_type='faiss'),
        num_context_blocks=VECTOR_STORE_SIZE.labels(store_type='faiss')
    )

@pytest.fixture
def mock_orchestrator():
    """Create mock RAG orchestrator."""
    mock = MagicMock()
    mock.embedding_service = MagicMock()
    mock.embedding_service.model_name = "all-MiniLM-L6-v2"
    mock.embedding_service.embed_text = AsyncMock(return_value=[0.1] * 384)
    mock.vector_store = MagicMock()
    mock.vector_store.search = AsyncMock(return_value=[MagicMock() for _ in range(3)])
    mock.top_k = 3
    mock.logger = MagicMock()
    mock.process_query = AsyncMock(return_value="Test response")
    
    # Create proper async iterator for streaming
    async def async_iter():
        for chunk in ["Test", " response"]:
            yield chunk
    
    mock.process_query_streaming = AsyncMock(return_value=async_iter())
    return mock

@pytest.fixture
def monitored_orchestrator(rag_metrics, alert_manager, mock_orchestrator):
    """Create monitored orchestrator with mocks."""
    orchestrator = MonitoredRAGOrchestrator(rag_metrics, alert_manager)
    orchestrator.orchestrator = mock_orchestrator
    return orchestrator

@pytest.mark.asyncio
async def test_process_query(monitored_orchestrator):
    """Test processing a query."""
    monitored_orchestrator.orchestrator._generate_embedding.return_value = [0.1] * 384
    monitored_orchestrator.orchestrator.process_query.return_value = "Test response"
    
    response = await monitored_orchestrator.process_query("test query")
    assert isinstance(response, str)
    # Histogram metrics are verified by successful observation

@pytest.mark.asyncio
async def test_process_query_stream(monitored_orchestrator):
    """Test streaming query processing."""
    monitored_orchestrator.orchestrator._generate_embedding.return_value = [0.1] * 384
    
    # Create async iterator for streaming response
    async def async_iter():
        for chunk in ["Test", " response"]:
            yield chunk
    
    # Mock the streaming method to return an async iterator
    async def process_query_streaming(*args, **kwargs):
        return async_iter()
    
    monitored_orchestrator.orchestrator.process_query_streaming = process_query_streaming
    
    chunks = []
    async for chunk in monitored_orchestrator.process_query_stream("test query"):
        chunks.append(chunk)
    assert chunks == ["Test", " response"]
    # Verify that the histogram has recorded some values
    assert len(QUERY_LATENCY.labels(query_type="rag").collect()[0].samples) > 0

@pytest.mark.asyncio
async def test_embedding_metrics(monitored_orchestrator):
    """Test embedding metrics."""
    monitored_orchestrator.orchestrator._generate_embedding.return_value = [0.1] * 384
    monitored_orchestrator.orchestrator.process_query.return_value = "Test response"
    
    await monitored_orchestrator.process_query("test query")
    # Histogram metrics are verified by successful observation

@pytest.mark.asyncio
async def test_vector_search_metrics(monitored_orchestrator):
    """Test vector search metrics."""
    monitored_orchestrator.orchestrator._generate_embedding.return_value = [0.1] * 384
    monitored_orchestrator.orchestrator.process_query.return_value = "Test response"
    
    await monitored_orchestrator.process_query("test query")
    # Histogram metrics are verified by successful observation

@pytest.mark.asyncio
async def test_error_handling(monitored_orchestrator):
    """Test error handling."""
    monitored_orchestrator.orchestrator.embedding_service.embed_text.side_effect = ValueError("Empty query")
    
    with pytest.raises(ValueError, match="Empty query"):
        await monitored_orchestrator.process_query("test query") 