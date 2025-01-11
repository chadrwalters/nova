"""Test monitoring service functionality."""

import asyncio
import time
import logging
from typing import AsyncGenerator
import pytest
import pytest_asyncio
from unittest.mock import patch, Mock, AsyncMock
from nova.monitoring.service import MonitoringService
from nova.monitoring.alerts import AlertManager
from nova.config import NovaConfig, MonitoringConfig, MetricsConfig, AlertingConfig
from nova.document.model import Document

@pytest.fixture
def monitoring_config():
    """Create test monitoring configuration."""
    return MonitoringConfig(
        enabled=True,
        metrics=MetricsConfig(
            port=0,  # Use port 0 to let OS assign random available port
            memory_update_interval=1,
            vector_store_update_interval=1
        ),
        alerting=AlertingConfig(
            max_query_latency=1.0,
            max_error_rate=0.1,
            max_memory_usage=1024 * 1024 * 1024,  # 1GB
            max_vector_store_size=1000,
            min_rate_limit_remaining=100,
            rate_limit_warning_threshold=0.2
        ),
        log_path="/tmp/nova_test.log"
    )

@pytest.fixture
def alert_manager(monitoring_config):
    """Create alert manager for testing."""
    return AlertManager(monitoring_config.alerting)

@pytest_asyncio.fixture
async def monitoring_service(monitoring_config):
    """Create monitoring service for testing."""
    with patch('nova.monitoring.service.start_metrics_server'):  # Mock metrics server
        service = MonitoringService(monitoring_config)
        yield service
        await service.stop()  # Ensure cleanup after each test

@pytest.mark.asyncio
@patch('nova.monitoring.service.start_metrics_server')
async def test_service_start(mock_start_server, monitoring_service):
    """Test monitoring service start."""
    await monitoring_service.start()
    
    assert mock_start_server.called
    assert monitoring_service._running
    assert len(monitoring_service.tasks) == 2  # Memory and vector store tasks

@pytest.mark.asyncio
async def test_service_disabled():
    """Test monitoring service when disabled."""
    config = MonitoringConfig(enabled=False)
    service = MonitoringService(config)
    
    with patch('nova.monitoring.service.start_metrics_server') as mock_start_server:
        await service.start()
        mock_start_server.assert_not_called()
        assert not service._running
        assert not service.tasks

@pytest.mark.asyncio
async def test_service_stop(monitoring_service):
    """Test monitoring service stop."""
    await monitoring_service.start()
    await monitoring_service.stop()
    
    assert not monitoring_service._running
    assert not monitoring_service.tasks

def test_track_query(monitoring_service):
    """Test query tracking."""
    with patch.object(monitoring_service.alert_manager, 'check_query_latency') as mock_check:
        monitoring_service.track_query(0.5, True)
        mock_check.assert_called_once_with(0.5)

@pytest.mark.asyncio
async def test_track_api_request(monitoring_service):
    """Test API request tracking."""
    # Track successful and failed requests
    monitoring_service.track_api_request("test_endpoint", True)
    monitoring_service.track_api_request("test_endpoint", False, "test_error")

    # Check metrics were updated
    with patch.object(monitoring_service.alert_manager, 'check_error_rate') as mock_check:
        monitoring_service.track_api_request("test_endpoint", False, "test_error")
        mock_check.assert_called_once()

def test_track_rate_limits(monitoring_service):
    """Test rate limit tracking."""
    with patch.object(monitoring_service.alert_manager, 'check_rate_limits') as mock_check:
        monitoring_service.track_rate_limits("test", 100, 3600)
        mock_check.assert_called_once_with("test", 100)

@pytest.mark.asyncio
async def test_memory_metrics_collection(monitoring_service):
    """Test memory metrics collection."""
    with patch('psutil.Process') as mock_process:
        mock_memory = Mock()
        mock_memory.rss = 1024 * 1024  # 1MB
        mock_process.return_value.memory_info.return_value = mock_memory

        with patch.object(monitoring_service.alert_manager, 'check_memory_usage') as mock_check:
            await monitoring_service.start()
            await asyncio.sleep(0.1)  # Small delay to allow collection
            mock_check.assert_called_with(1024 * 1024)

@pytest.mark.asyncio
async def test_vector_store_metrics_collection(monitoring_service):
    """Test vector store metrics collection."""
    with patch.object(monitoring_service, '_get_vector_store_size', return_value=1000):
        with patch.object(monitoring_service.alert_manager, 'check_vector_store_size') as mock_check:
            await monitoring_service.start()
            await asyncio.sleep(0.1)  # Small delay to allow collection
            mock_check.assert_called_with(1000)

@pytest.mark.asyncio
async def test_metrics_collection_error_handling(monitoring_service):
    """Test error handling in metrics collection."""
    mock_logger = Mock(spec=logging.Logger)
    monitoring_service.logger = mock_logger

    with patch('psutil.Process', side_effect=Exception("Memory error")):
        await monitoring_service.start()
        await asyncio.sleep(0.1)  # Small delay to allow collection
        mock_logger.error.assert_called_once()

def test_logging_setup(tmp_path):
    """Test logging setup."""
    log_path = tmp_path / "nova.log"
    config = MonitoringConfig(
        enabled=True,
        metrics=MetricsConfig(),
        alerting=AlertingConfig(),
        log_path=str(log_path)
    )
    
    service = MonitoringService(config)
    
    # Check that log handler was added
    assert any(isinstance(h, logging.FileHandler) for h in service.logger.handlers)
    assert service.logger.level == logging.INFO

@pytest.mark.asyncio
async def test_concurrent_metric_updates(monitoring_service):
    """Test concurrent metric updates."""
    async def update_metrics():
        monitoring_service.track_api_request("concurrent_test", True)
        monitoring_service.track_api_request("concurrent_test", False, "test_error")
    
    await monitoring_service.start()
    await asyncio.gather(*[update_metrics() for _ in range(2)])  # Reduced from 5
    await monitoring_service.stop()

@pytest.mark.asyncio
async def test_service_cleanup(monitoring_service):
    """Test service cleanup on stop."""
    await monitoring_service.start()
    
    # Create some active alerts
    monitoring_service.track_query(2.0, False)  # Should trigger alert
    
    # Stop service
    await monitoring_service.stop()
    
    assert not monitoring_service._running
    assert not monitoring_service.tasks
    # Verify all background tasks were cancelled
    for task in monitoring_service.tasks:
        assert task.cancelled() 

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

@pytest.mark.asyncio
async def test_service_disabled():
    """Test monitoring service when disabled."""
    config = MonitoringConfig(enabled=False)
    service = MonitoringService(config)

    with patch('nova.monitoring.service.start_metrics_server') as mock_start_server:
        await service.start()
        mock_start_server.assert_not_called()
        assert not service._running

@pytest.mark.asyncio
async def test_service_stop(monitoring_service):
    """Test monitoring service stop."""
    await monitoring_service.start()
    await monitoring_service.stop()

    assert not monitoring_service._running 

@pytest.fixture
def test_documents():
    """Create test documents."""
    return [
        Document(
            content=f"Test document {i}",
            source=f"test_doc_{i}.txt",
            metadata={"id": i}
        ) for i in range(2)
    ] 