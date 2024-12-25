"""Cache management utilities."""

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union
from collections import OrderedDict

logger = logging.getLogger(__name__)

class CacheManager:
    """Manages caching of processed data."""
    
    def __init__(
        self,
        cache_dir: Optional[Union[str, Path]] = None,
        max_size_bytes: Optional[int] = None,
        provider: str = "grok",
        default_ttl: int = 24 * 60 * 60,  # 24 hours default
        memory_entries: int = 100  # Max memory cache entries
    ) -> None:
        """Initialize cache manager.
        
        Args:
            cache_dir: Directory to store cache files
            max_size_bytes: Maximum cache size in bytes
            provider: Provider name for cache key generation
            default_ttl: Default time-to-live in seconds
            memory_entries: Maximum number of entries to keep in memory
        """
        self.cache_dir = Path(cache_dir) if cache_dir else None
        self.provider = provider
        self.max_size_bytes = max_size_bytes if max_size_bytes else 1024 * 1024 * 1024  # Default 1GB
        self.default_ttl = default_ttl
        self.memory_entries = memory_entries
        
        # Initialize memory cache
        self._memory_cache = OrderedDict()
        self._memory_ttls = {}
        
        # Initialize stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'invalidations': 0,
            'evictions': 0,
            'expirations': 0,
            'memory_hits': 0,
            'memory_misses': 0,
            'provider_stats': {},
            'cache_size': 0,
            'hit_ratio': 0.0
        }
        
        # Initialize provider stats
        for prov in ['grok', 'openai']:
            self.stats['provider_stats'][prov] = {
                'hits': 0,
                'misses': 0,
                'errors': 0,
                'invalidations': 0,
                'expirations': 0
            }
        
        if self.cache_dir:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
            # Create provider directories
            for prov in ['grok', 'openai']:
                (self.cache_dir / prov).mkdir(exist_ok=True)
            logger.debug("Initialized cache in %s", self.cache_dir)
    
    def _get_cache_size(self) -> int:
        """Get current cache size in bytes."""
        if not self.cache_dir:
            return 0
        
        total_size = 0
        for root, _, files in os.walk(self.cache_dir):
            for file in files:
                file_path = Path(root) / file
                total_size += file_path.stat().st_size
        
        return total_size
    
    def _cleanup_old_files(self, max_age: Optional[int] = None) -> None:
        """Clean up old cache files.
        
        Args:
            max_age: Maximum age in seconds
        """
        if not self.cache_dir:
            return
        
        current_time = time.time()
        for root, _, files in os.walk(self.cache_dir):
            for file in files:
                file_path = Path(root) / file
                try:
                    if max_age and (current_time - file_path.stat().st_mtime) > max_age:
                        file_path.unlink()
                        self.stats['expirations'] += 1
                except OSError:
                    self.stats['errors'] += 1
    
    def _enforce_size_limit(self) -> None:
        """Enforce cache size limit by removing old files."""
        if not self.cache_dir or not self.max_size_bytes:
            return
        
        current_size = self._get_cache_size()
        if current_size <= self.max_size_bytes:
            return
        
        # Get all cache files sorted by modification time
        cache_files = []
        for root, _, files in os.walk(self.cache_dir):
            for file in files:
                file_path = Path(root) / file
                try:
                    cache_files.append((file_path, file_path.stat().st_mtime))
                except OSError:
                    continue
        
        cache_files.sort(key=lambda x: x[1])  # Sort by mtime
        
        # Remove oldest files until under limit
        for file_path, _ in cache_files:
            try:
                file_path.unlink()
                self.stats['evictions'] += 1
                current_size = self._get_cache_size()
                if current_size <= self.max_size_bytes:
                    break
            except OSError:
                self.stats['errors'] += 1
    
    def _generate_cache_key(self, image_path: Union[str, Path]) -> str:
        """Generate cache key from image path and metadata.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Cache key string
        """
        path = Path(image_path)
        if not path.exists():
            return f"nonexistent_{path.name}"
            
        stats = path.stat()
        return f"{path.stem}_{stats.st_size}_{int(stats.st_mtime)}"
    
    def _get_cache_path(self, key: str, provider: str) -> Path:
        """Get cache file path for key and provider."""
        if not self.cache_dir:
            raise ValueError("Cache directory not set")
        return self.cache_dir / provider / f"{key}.json"
    
    def _update_hit_stats(self, provider: str) -> None:
        """Update hit statistics."""
        self.stats['hits'] += 1
        if provider in self.stats['provider_stats']:
            self.stats['provider_stats'][provider]['hits'] += 1
        self._update_hit_ratio()
    
    def _update_miss_stats(self, provider: str) -> None:
        """Update miss statistics."""
        self.stats['misses'] += 1
        if provider in self.stats['provider_stats']:
            self.stats['provider_stats'][provider]['misses'] += 1
        self._update_hit_ratio()
    
    def _update_error_stats(self, provider: str) -> None:
        """Update error statistics."""
        self.stats['errors'] += 1
        if provider in self.stats['provider_stats']:
            self.stats['provider_stats'][provider]['errors'] += 1
    
    def _update_hit_ratio(self) -> None:
        """Update cache hit ratio."""
        total = self.stats['hits'] + self.stats['misses']
        if total > 0:
            self.stats['hit_ratio'] = self.stats['hits'] / total
    
    def get(self, image_path: Union[str, Path], provider: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get cached data.
        
        Args:
            image_path: Path to image file
            provider: Optional provider override
            
        Returns:
            Cached data if found and valid, None otherwise
        """
        provider = provider or self.provider
        key = self._generate_cache_key(image_path)
        
        # Try memory cache first
        memory_key = f"{provider}:{key}"
        if memory_key in self._memory_cache:
            data = self._memory_cache[memory_key]
            if self._memory_ttls.get(memory_key, float('inf')) > time.time():
                self.stats['memory_hits'] += 1
                self._update_hit_stats(provider)
                return data
            else:
                # Expired
                del self._memory_cache[memory_key]
                del self._memory_ttls[memory_key]
                self.stats['expirations'] += 1
        else:
            self.stats['memory_misses'] += 1
        
        # Try file cache
        try:
            cache_path = self._get_cache_path(key, provider)
            if not cache_path.exists():
                self._update_miss_stats(provider)
                return None
            
            # Check if file is too old
            if self.default_ttl and (time.time() - cache_path.stat().st_mtime) > self.default_ttl:
                cache_path.unlink()
                self.stats['expirations'] += 1
                self._update_miss_stats(provider)
                return None
            
            # Load cache data
            with open(cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate metadata
            metadata = data.get('_cache_metadata', {})
            if metadata.get('image_path') != str(image_path):
                self._update_miss_stats(provider)
                return None
            
            # Check if image has been modified
            path = Path(image_path)
            if path.exists():
                current_stats = path.stat()
                if (metadata.get('image_size') != current_stats.st_size or
                    metadata.get('image_mtime') != current_stats.st_mtime):
                    self.stats['invalidations'] += 1
                    self._update_miss_stats(provider)
                    return None
            
            # Update memory cache
            self._memory_cache[memory_key] = data
            self._memory_ttls[memory_key] = time.time() + self.default_ttl
            
            # Enforce memory cache size
            while len(self._memory_cache) > self.memory_entries:
                oldest_key = next(iter(self._memory_cache))
                del self._memory_cache[oldest_key]
                del self._memory_ttls[oldest_key]
                self.stats['evictions'] += 1
            
            self._update_hit_stats(provider)
            return data
            
        except Exception as e:
            logger.error("Error reading cache: %s", str(e))
            self._update_error_stats(provider)
            return None
    
    def set(self, image_path: Union[str, Path], provider: str, data: Dict[str, Any]) -> None:
        """Set cache data.
        
        Args:
            image_path: Path to image file
            provider: Provider name
            data: Data to cache
        """
        if not self.cache_dir:
            return
        
        try:
            # Add metadata
            path = Path(image_path)
            if path.exists():
                stats = path.stat()
                data['_cache_metadata'] = {
                    'provider': provider,
                    'image_path': str(image_path),
                    'image_size': stats.st_size,
                    'image_mtime': stats.st_mtime,
                    'timestamp': time.time()
                }
            
            # Save to file
            key = self._generate_cache_key(image_path)
            cache_path = self._get_cache_path(key, provider)
            
            with open(cache_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            
            # Update memory cache
            memory_key = f"{provider}:{key}"
            self._memory_cache[memory_key] = data
            self._memory_ttls[memory_key] = time.time() + self.default_ttl
            
            # Enforce memory cache size
            while len(self._memory_cache) > self.memory_entries:
                oldest_key = next(iter(self._memory_cache))
                del self._memory_cache[oldest_key]
                del self._memory_ttls[oldest_key]
                self.stats['evictions'] += 1
            
            # Enforce size limit
            self._enforce_size_limit()
            
        except Exception as e:
            logger.error("Error writing cache: %s", str(e))
            self._update_error_stats(provider)
    
    def clear(self, provider: Optional[str] = None) -> None:
        """Clear cache entries.
        
        Args:
            provider: Optional provider to clear cache for
        """
        if not self.cache_dir:
            return
            
        if provider:
            provider_dir = self.cache_dir / provider
            if provider_dir.exists():
                for f in provider_dir.glob('*.json'):
                    f.unlink()
        else:
            for prov in ['grok', 'openai']:
                provider_dir = self.cache_dir / prov
                if provider_dir.exists():
                    for f in provider_dir.glob('*.json'):
                        f.unlink()
        
        # Clear memory cache
        self._memory_cache.clear()
        self._memory_ttls.clear()
        
        # Reset stats
        self.stats = {
            'hits': 0,
            'misses': 0,
            'errors': 0,
            'invalidations': 0,
            'evictions': 0,
            'expirations': 0,
            'memory_hits': 0,
            'memory_misses': 0,
            'provider_stats': {},
            'cache_size': 0,
            'hit_ratio': 0.0
        }
        
        # Reset provider stats
        for prov in ['grok', 'openai']:
            self.stats['provider_stats'][prov] = {
                'hits': 0,
                'misses': 0,
                'errors': 0,
                'invalidations': 0,
                'expirations': 0
            }
    
    def cleanup(self, max_age: Optional[int] = None, provider: Optional[str] = None) -> None:
        """Clean up old cache entries.
        
        Args:
            max_age: Maximum age in seconds
            provider: Optional provider to clean
        """
        if not self.cache_dir:
            return
            
        current_time = time.time()
        
        def clean_provider(prov: str) -> None:
            provider_dir = self.cache_dir / prov
            if provider_dir.exists():
                for f in provider_dir.glob('*.json'):
                    try:
                        if max_age and (current_time - f.stat().st_mtime) > max_age:
                            f.unlink()
                            self.stats['expirations'] += 1
                    except OSError:
                        self.stats['errors'] += 1
        
        if provider:
            clean_provider(provider)
        else:
            for prov in ['grok', 'openai']:
                clean_provider(prov)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary of cache statistics
        """
        # Update cache size
        self.stats['cache_size'] = self._get_cache_size()
        
        # Update hit ratio
        total = self.stats['hits'] + self.stats['misses']
        if total > 0:
            self.stats['hit_ratio'] = self.stats['hits'] / total
        
        return self.stats
