"""Caching module for API responses."""

from typing import Any, Dict, Optional, TypeVar, Callable
from datetime import datetime, timedelta
import functools
import gzip
import json
import logging
from dataclasses import dataclass
from nova.monitoring.alerts import alert_json_dumps

logger = logging.getLogger(__name__)

T = TypeVar('T')

@dataclass
class CacheEntry:
    """Cache entry with data and metadata."""
    data: bytes  # Compressed data
    expires_at: datetime
    etag: str

class ResponseCache:
    """Cache for API responses with compression."""

    def __init__(self, default_ttl: int = 60):
        """Initialize cache.

        Args:
            default_ttl: Default time-to-live in seconds
        """
        self._cache: Dict[str, CacheEntry] = {}
        self._default_ttl = default_ttl

    def _compress(self, data: Any) -> bytes:
        """Compress data using gzip."""
        return gzip.compress(alert_json_dumps(data).encode())

    def _decompress(self, data: bytes) -> Any:
        """Decompress gzipped data."""
        return json.loads(gzip.decompress(data).decode())

    def _generate_etag(self, data: bytes) -> str:
        """Generate ETag for cache validation."""
        import hashlib
        return hashlib.md5(data).hexdigest()

    def get(self, key: str) -> Optional[tuple[Any, str]]:
        """Get cached response and ETag if available and not expired."""
        if key not in self._cache:
            return None

        entry = self._cache[key]
        if datetime.now() > entry.expires_at:
            del self._cache[key]
            return None

        return self._decompress(entry.data), entry.etag

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> str:
        """Cache response with optional TTL.

        Args:
            key: Cache key
            value: Data to cache
            ttl: Time-to-live in seconds

        Returns:
            ETag for the cached response
        """
        compressed = self._compress(value)
        etag = self._generate_etag(compressed)

        self._cache[key] = CacheEntry(
            data=compressed,
            expires_at=datetime.now() + timedelta(seconds=ttl or self._default_ttl),
            etag=etag
        )

        return etag

    def invalidate(self, key: str) -> None:
        """Remove entry from cache."""
        self._cache.pop(key, None)

def cached_response(ttl: Optional[int] = None):
    """Decorator for caching API responses.

    Args:
        ttl: Time-to-live in seconds
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            # Get cache instance from first arg (self)
            instance = args[0]
            if not hasattr(instance, '_response_cache'):
                instance._response_cache = ResponseCache()

            # Generate cache key from function name and arguments
            key = f"{func.__name__}:{hash(str(args[1:]))}-{hash(str(kwargs))}"

            # Check cache
            cached = instance._response_cache.get(key)
            if cached is not None:
                data, etag = cached
                return data

            # Get fresh response
            response = await func(*args, **kwargs)

            # Cache response
            instance._response_cache.set(key, response, ttl)

            return response
        return wrapper
    return decorator
