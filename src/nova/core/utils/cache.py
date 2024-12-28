"""Cache management utilities."""

import os
import shutil
import logging
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


class CacheManager:
    """Manages caching for pipeline phases."""

    def __init__(
        self,
        directory: Path,
        max_size_mb: int = 1024,
        max_age_days: int = 7,
        cleanup_on_start: bool = True,
        cleanup_on_error: bool = True
    ):
        """Initialize cache manager.
        
        Args:
            directory: Cache directory path
            max_size_mb: Maximum cache size in MB
            max_age_days: Maximum age of cache files in days
            cleanup_on_start: Whether to clean up cache on start
            cleanup_on_error: Whether to clean up cache on error
        """
        self.directory = directory
        self.max_size_mb = max_size_mb
        self.max_age_days = max_age_days
        self.cleanup_on_start = cleanup_on_start
        self.cleanup_on_error = cleanup_on_error
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        """Initialize cache directory.
        
        Creates cache directory if it doesn't exist and performs cleanup if enabled.
        """
        # Create cache directory if it doesn't exist
        self.directory.mkdir(parents=True, exist_ok=True)

        # Clean up cache if enabled
        if self.cleanup_on_start:
            await self.cleanup()

    async def cleanup(self):
        """Clean up cache directory.
        
        Removes old cache files and ensures cache size is within limits.
        """
        try:
            # Remove old files
            cutoff_date = datetime.now() - timedelta(days=self.max_age_days)
            for file_path in self.directory.glob('**/*'):
                if file_path.is_file():
                    mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if mtime < cutoff_date:
                        file_path.unlink()

            # Check cache size
            total_size = sum(f.stat().st_size for f in self.directory.glob('**/*') if f.is_file())
            if total_size > self.max_size_mb * 1024 * 1024:
                # Remove oldest files until under limit
                files = [(f, f.stat().st_mtime) for f in self.directory.glob('**/*') if f.is_file()]
                files.sort(key=lambda x: x[1])  # Sort by modification time
                
                for file_path, _ in files:
                    file_path.unlink()
                    total_size = sum(f.stat().st_size for f in self.directory.glob('**/*') if f.is_file())
                    if total_size <= self.max_size_mb * 1024 * 1024:
                        break

        except Exception as e:
            self.logger.error(f"Error cleaning up cache: {e}")

    def get_cache_path(self, key: str) -> Path:
        """Get cache file path for key.
        
        Args:
            key: Cache key
            
        Returns:
            Path to cache file
        """
        return self.directory / key

    async def get(self, key: str) -> Optional[bytes]:
        """Get cached data.
        
        Args:
            key: Cache key
            
        Returns:
            Cached data or None if not found
        """
        try:
            cache_path = self.get_cache_path(key)
            if cache_path.exists():
                return cache_path.read_bytes()
        except Exception as e:
            self.logger.error(f"Error reading from cache: {e}")
        return None

    async def set(self, key: str, data: bytes):
        """Set cached data.
        
        Args:
            key: Cache key
            data: Data to cache
        """
        try:
            cache_path = self.get_cache_path(key)
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
        except Exception as e:
            self.logger.error(f"Error writing to cache: {e}")

    async def delete(self, key: str):
        """Delete cached data.
        
        Args:
            key: Cache key
        """
        try:
            cache_path = self.get_cache_path(key)
            if cache_path.exists():
                cache_path.unlink()
        except Exception as e:
            self.logger.error(f"Error deleting from cache: {e}")

    async def clear(self):
        """Clear all cached data."""
        try:
            if self.directory.exists():
                shutil.rmtree(self.directory)
            self.directory.mkdir(parents=True)
        except Exception as e:
            self.logger.error(f"Error clearing cache: {e}")

    def get_size(self) -> int:
        """Get current cache size in bytes.
        
        Returns:
            Cache size in bytes
        """
        try:
            return sum(f.stat().st_size for f in self.directory.glob('**/*') if f.is_file())
        except Exception as e:
            self.logger.error(f"Error getting cache size: {e}")
            return 0

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics.
        
        Returns:
            Dictionary containing cache statistics
        """
        try:
            files = list(self.directory.glob('**/*'))
            return {
                'size_bytes': sum(f.stat().st_size for f in files if f.is_file()),
                'file_count': len([f for f in files if f.is_file()]),
                'directory_count': len([f for f in files if f.is_dir()]),
                'oldest_file': min((f.stat().st_mtime for f in files if f.is_file()), default=0),
                'newest_file': max((f.stat().st_mtime for f in files if f.is_file()), default=0)
            }
        except Exception as e:
            self.logger.error(f"Error getting cache stats: {e}")
            return {}
