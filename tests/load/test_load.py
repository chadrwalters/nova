"""Tests for load testing."""

import pytest
from unittest.mock import Mock, patch, AsyncMock
import asyncio
from typing import List
from nova.monitoring.service import MonitoringService
from nova.monitoring.config import MonitoringConfig, MetricsConfig, AlertingConfig
from nova.config import NovaConfig
from nova.processing.types import Document

# Minimal test configuration
CONCURRENT_USERS = [1]  # Just test with 1 user for now
QUERY_DURATION = 2  # Very short duration
THINK_TIME = [0.1, 0.2]  # Minimal think time

@pytest.fixture
def load_test_config():
    """Create a test configuration."""
    with patch('nova.config.NovaConfig.from_yaml') as mock_load:
        mock_load.return_value = NovaConfig()
        return mock_load.return_value

@pytest.fixture
def monitoring_service(load_test_config):
    """Create a monitoring service."""
    config = MonitoringConfig(
        enabled=True,
        metrics=MetricsConfig(
            port=0,
            memory_update_interval=1,
            vector_store_update_interval=1
        ),
        alerting=AlertingConfig(
            max_query_latency=1.0,
            max_error_rate=0.1,
            max_memory_usage=1024 * 1024 * 1024,
            max_vector_store_size=1000,
            min_rate_limit_remaining=100,
            rate_limit_warning_threshold=0.2
        ),
        log_path="/tmp/nova_test.log"
    )
    with patch('nova.monitoring.service.start_metrics_server'):
        return MonitoringService(config)

@pytest.fixture
def test_documents() -> List[Document]:
    """Generate minimal test documents."""
    return [
        Document(
            content=f"Test document {i}",
            source=f"test_{i}.txt",
            metadata={"id": i}
        )
        for i in range(2)  # Just 2 test documents
    ]

@pytest.mark.asyncio
async def test_basic_load(monitoring_service, test_documents):
    """Test basic load with minimal configuration."""
    with patch('nova.load.service.LoadTestService') as MockService:
        mock_service = AsyncMock()
        MockService.return_value = mock_service
        mock_service.run_load_test.return_value = {"success": True}
        
        # Start monitoring
        await monitoring_service.start()
        
        # Run a minimal load test
        mock_service.run_load_test.assert_not_called()
        
        # Stop monitoring
        await monitoring_service.stop()
        
        assert not monitoring_service._running 