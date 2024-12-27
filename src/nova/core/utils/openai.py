"""OpenAI utilities."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union
import json

from ..errors import PipelineError
from .paths import ensure_directory

class OpenAICache:
    """Cache for OpenAI API responses."""
    
    def __init__(self, cache_dir: Union[str, Path]):
        """Initialize OpenAI cache.
        
        Args:
            cache_dir: Cache directory path
        """
        self.cache_dir = Path(cache_dir)
        ensure_directory(self.cache_dir)
        
    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Get cached response.
        
        Args:
            key: Cache key
            
        Returns:
            Cached response or None if not found
        """
        try:
            cache_file = self.cache_dir / f"{key}.json"
            if not cache_file.exists():
                return None
                
            return json.loads(cache_file.read_text())
            
        except Exception as e:
            raise PipelineError(f"Failed to get cached response: {e}")
            
    def set(self, key: str, response: Dict[str, Any]) -> None:
        """Set cached response.
        
        Args:
            key: Cache key
            response: Response to cache
        """
        try:
            cache_file = self.cache_dir / f"{key}.json"
            cache_file.write_text(json.dumps(response, indent=2))
            
        except Exception as e:
            raise PipelineError(f"Failed to cache response: {e}")
            
    def clear(self) -> None:
        """Clear cache."""
        try:
            for file in self.cache_dir.glob("*.json"):
                file.unlink()
                
        except Exception as e:
            raise PipelineError(f"Failed to clear cache: {e}")
            
    def __str__(self) -> str:
        """Get string representation.
        
        Returns:
            String representation
        """
        return f"OpenAICache(cache_dir={self.cache_dir})" 