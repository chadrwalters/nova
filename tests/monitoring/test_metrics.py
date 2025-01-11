"""Test monitoring metrics functionality."""
import time
import asyncio
import pytest
from prometheus_client import Counter, Histogram, Gauge
from nova.monitoring.metrics import (
    QUERY_LATENCY,
    QUERY_ERRORS,
    VECTOR_STORE_SIZE,
    VECTOR_STORE_MEMORY,
    VECTOR_STORE_VECTORS,
    API_REQUESTS,
    API_ERRORS,
    RATE_LIMITS_REMAINING,
    RATE_LIMIT_RESETS,
    track_time,
    update_memory_usage,
    update_vector_store_metrics,
    record_api_request,
    record_api_error,
    update_rate_limits
)

@pytest.fixture(autouse=True)
def setup_metrics():
    """Set up metrics with proper labels."""
    QUERY_LATENCY.labels(query_type="test")
    QUERY_ERRORS.labels(error_type="test")
    API_REQUESTS.labels(service="test")
    API_ERRORS.labels(service="test", error_type="test")
    VECTOR_STORE_SIZE.labels(store_type="test")
    VECTOR_STORE_MEMORY.labels(store_type="test")
    VECTOR_STORE_VECTORS.labels(store_type="test")
    RATE_LIMITS_REMAINING.labels(service="test")
    RATE_LIMIT_RESETS.labels(service="test")

def test_query_latency_histogram():
    """Test query latency histogram metric."""
    QUERY_LATENCY.labels(query_type="test").observe(1.5)
    samples = list(QUERY_LATENCY.collect()[0].samples)
    assert any(s.value > 0 for s in samples)

def test_query_errors_counter():
    """Test query errors counter metric."""
    # Clear existing metrics
    QUERY_ERRORS._metrics.clear()
    
    # Increment with test label
    QUERY_ERRORS.labels(error_type="test").inc()
    
    # Get samples and verify
    samples = list(QUERY_ERRORS.collect()[0].samples)
    assert samples[0].value == 1
    assert samples[0].labels["error_type"] == "test"

def test_track_time_decorator():
    """Test track_time decorator."""
    metric = QUERY_LATENCY.labels(query_type="test")
    
    @track_time(metric)
    def slow_function():
        time.sleep(0.1)
        return "done"
    
    result = slow_function()
    assert result == "done"
    
    samples = list(QUERY_LATENCY.collect()[0].samples)
    assert any(s.value > 0 for s in samples)

def test_update_vector_store_metrics():
    """Test updating vector store metrics."""
    total_vectors = 1000
    memory_usage = 1024 * 1024  # 1MB
    index_size = 2048 * 1024  # 2MB
    
    update_vector_store_metrics(total_vectors, memory_usage, index_size)
    
    # Check vector count
    vectors_samples = list(VECTOR_STORE_VECTORS.collect()[0].samples)
    test_vectors = next(s.value for s in vectors_samples if s.labels["store_type"] == "test")
    assert test_vectors == total_vectors
    
    # Check memory usage
    memory_samples = list(VECTOR_STORE_MEMORY.collect()[0].samples)
    test_memory = next(s.value for s in memory_samples if s.labels["store_type"] == "test")
    assert test_memory == memory_usage
    
    # Check index size
    size_samples = list(VECTOR_STORE_SIZE.collect()[0].samples)
    test_size = next(s.value for s in size_samples if s.labels["store_type"] == "test")
    assert test_size == index_size

def test_api_request_tracking():
    """Test API request tracking metrics."""
    record_api_request("test")
    record_api_request("test")
    
    samples = list(API_REQUESTS.collect()[0].samples)
    test_count = next(s.value for s in samples if s.labels["service"] == "test")
    assert test_count == 2

def test_api_error_tracking():
    """Test API error tracking metrics."""
    record_api_error("test", "test")
    record_api_error("test", "test")
    
    samples = list(API_ERRORS.collect()[0].samples)
    test_errors = next(s.value for s in samples if s.labels["service"] == "test")
    assert test_errors == 2

def test_rate_limit_tracking():
    """Test rate limit tracking metrics."""
    current_time = time.time()
    update_rate_limits("test", 100, int(current_time + 3600))
    
    remaining_samples = list(RATE_LIMITS_REMAINING.collect()[0].samples)
    reset_samples = list(RATE_LIMIT_RESETS.collect()[0].samples)
    
    test_remaining = next(s.value for s in remaining_samples if s.labels["service"] == "test")
    test_reset = next(s.value for s in reset_samples if s.labels["service"] == "test")
    
    assert test_remaining == 100
    assert test_reset > current_time

@pytest.mark.asyncio
async def test_track_time_async():
    """Test track_time decorator with async functions."""
    metric = QUERY_LATENCY.labels(query_type="test")
    
    @track_time(metric)
    async def slow_async_function():
        await asyncio.sleep(0.1)
        return "done"
    
    result = await slow_async_function()
    assert result == "done"
    
    samples = list(QUERY_LATENCY.collect()[0].samples)
    assert any(s.value > 0 for s in samples)

@pytest.mark.asyncio
async def test_concurrent_metric_updates():
    """Test concurrent metric updates."""
    # Reset the counter before test
    API_REQUESTS.labels(service="test")._value.set(0)
    
    async def update_metrics():
        for _ in range(10):
            record_api_request("test")
            await asyncio.sleep(0.01)
    
    # Run multiple concurrent updates
    tasks = [update_metrics() for _ in range(5)]
    await asyncio.gather(*tasks)
    
    samples = list(API_REQUESTS.collect()[0].samples)
    test_count = next(s.value for s in samples if s.labels["service"] == "test")
    assert test_count == 50  # 5 tasks * 10 updates each 