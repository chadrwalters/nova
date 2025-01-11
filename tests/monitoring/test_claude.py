"""Tests for Claude monitoring."""
import asyncio
import pytest
from nova.monitoring.claude import ClaudeMonitor, MonitoredClaudeClient
from nova.monitoring.alerts import AlertManager
from nova.monitoring.metrics import API_REQUESTS, API_ERRORS, RATE_LIMITS_REMAINING, RATE_LIMIT_RESETS
from nova.config import AlertingConfig
from unittest.mock import MagicMock, AsyncMock

@pytest.fixture
def alert_manager():
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
def claude_monitor(alert_manager):
    return ClaudeMonitor(alert_manager)

@pytest.fixture
def monitored_client(claude_monitor, alert_manager):
    mock_client = MagicMock()
    mock_client.complete = AsyncMock(return_value="Test response")
    
    # Create proper async iterator for streaming
    async def async_iter():
        for chunk in ["Test", " response"]:
            yield chunk
    
    mock_client.complete_stream = AsyncMock(return_value=async_iter())
    return MonitoredClaudeClient(claude_monitor, mock_client)

async def async_iter(items):
    for item in items:
        yield item

@pytest.fixture(autouse=True)
def setup_metrics():
    """Set up metrics with proper labels."""
    # Clear existing metrics
    API_REQUESTS._metrics.clear()
    API_ERRORS._metrics.clear()
    RATE_LIMITS_REMAINING._metrics.clear()
    RATE_LIMIT_RESETS._metrics.clear()
    
    # Initialize with zero values
    API_REQUESTS.labels(service="claude")._value.set(0)
    API_ERRORS.labels(service="claude", error_type="test")._value.set(0)
    RATE_LIMITS_REMAINING.labels(service="claude")._value.set(0)
    RATE_LIMIT_RESETS.labels(service="claude")._value.set(0)

@pytest.mark.asyncio
async def test_record_request(claude_monitor):
    """Test recording API requests."""
    claude_monitor.record_request("test")
    assert API_REQUESTS.labels(service="claude")._value.get() == 1

@pytest.mark.asyncio
async def test_record_error(claude_monitor):
    """Test recording API errors."""
    claude_monitor.record_error("test")
    assert API_ERRORS.labels(service="claude", error_type="test")._value.get() == 1

@pytest.mark.asyncio
async def test_update_rate_limits(claude_monitor):
    """Test updating rate limits."""
    claude_monitor.update_rate_limits(remaining=100, reset_time=3600)
    assert RATE_LIMITS_REMAINING.labels(service="claude")._value.get() == 100

@pytest.mark.asyncio
async def test_check_rate_limit(claude_monitor):
    """Test checking rate limits."""
    claude_monitor.update_rate_limits(remaining=0, reset_time=3600)
    assert not claude_monitor.check_rate_limit()
    
    claude_monitor.update_rate_limits(remaining=100, reset_time=3600)
    assert claude_monitor.check_rate_limit()

@pytest.mark.asyncio
async def test_monitored_client_complete(monitored_client):
    """Test monitored client complete method."""
    response = await monitored_client.complete("test prompt")
    assert isinstance(response, str)
    assert API_REQUESTS.labels(service="claude")._value.get() == 1

@pytest.mark.asyncio
async def test_monitored_client_complete_stream(monitored_client):
    """Test monitored client streaming completion."""
    async for chunk in monitored_client.complete_stream("test prompt"):
        assert isinstance(chunk, str)
    assert API_REQUESTS.labels(service="claude")._value.get() == 1

@pytest.mark.asyncio
async def test_monitored_client_rate_limit(monitored_client, claude_monitor):
    """Test rate limit handling."""
    claude_monitor.update_rate_limits(remaining=0, reset_time=3600)
    with pytest.raises(ValueError, match="Rate limit exceeded"):
        await monitored_client.complete("test prompt") 