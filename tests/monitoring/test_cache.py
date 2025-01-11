"""Tests for response caching module."""

import pytest
from datetime import datetime, timedelta
import asyncio
import json
import gzip
from nova.monitoring.cache import ResponseCache, cached_response

@pytest.fixture
def cache():
    """Create a response cache instance."""
    return ResponseCache(default_ttl=60)

def test_cache_set_get():
    """Test basic cache set and get operations."""
    cache = ResponseCache()
    data = {"test": "data"}

    # Set data in cache
    etag = cache.set("test_key", data)
    assert etag is not None

    # Get data from cache
    cached_data = cache.get("test_key")
    assert cached_data is not None
    assert cached_data[0] == data
    assert cached_data[1] == etag

@pytest.mark.asyncio
async def test_cache_expiration():
    """Test cache entry expiration."""
    cache = ResponseCache(default_ttl=1)  # 1 second TTL
    data = {"test": "data"}

    # Set data in cache
    cache.set("test_key", data)

    # Get data immediately
    assert cache.get("test_key") is not None

    # Wait for expiration
    await asyncio.sleep(1.1)

    # Data should be expired
    assert cache.get("test_key") is None

def test_cache_invalidation():
    """Test manual cache invalidation."""
    cache = ResponseCache()
    data = {"test": "data"}

    # Set data in cache
    cache.set("test_key", data)
    assert cache.get("test_key") is not None

    # Invalidate cache entry
    cache.invalidate("test_key")
    assert cache.get("test_key") is None

def test_compression():
    """Test data compression."""
    cache = ResponseCache()
    data = {"test": "data" * 1000}  # Create large data

    # Set data in cache
    etag = cache.set("test_key", data)

    # Get compressed data directly from cache
    compressed = cache._cache["test_key"].data

    # Verify compression
    assert len(compressed) < len(json.dumps(data).encode())

    # Verify data can be retrieved correctly
    cached_data = cache.get("test_key")
    assert cached_data is not None
    assert cached_data[0] == data

@pytest.mark.asyncio
async def test_cached_response_decorator():
    """Test cached_response decorator."""
    class TestAPI:
        def __init__(self):
            self.counter = 0

        @cached_response(ttl=60)
        async def test_endpoint(self, param: str) -> dict:
            self.counter += 1
            return {"param": param, "count": self.counter}

    api = TestAPI()

    # First call should increment counter
    result1 = await api.test_endpoint("test")
    assert result1["count"] == 1

    # Second call should return cached result
    result2 = await api.test_endpoint("test")
    assert result2["count"] == 1  # Counter shouldn't increment
    assert api.counter == 1  # Actual counter should still be 1

    # Different parameter should increment counter
    result3 = await api.test_endpoint("different")
    assert result3["count"] == 2
    assert api.counter == 2

@pytest.mark.asyncio
async def test_cached_response_expiration():
    """Test cached_response decorator with expiration."""
    class TestAPI:
        def __init__(self):
            self.counter = 0

        @cached_response(ttl=1)  # 1 second TTL
        async def test_endpoint(self) -> dict:
            self.counter += 1
            return {"count": self.counter}

    api = TestAPI()

    # First call
    result1 = await api.test_endpoint()
    assert result1["count"] == 1

    # Wait for cache expiration
    await asyncio.sleep(1.1)

    # Call after expiration should increment counter
    result2 = await api.test_endpoint()
    assert result2["count"] == 2
    assert api.counter == 2
