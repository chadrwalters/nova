"""OpenAI utilities for Nova document processor."""

import os
from pathlib import Path
from typing import Dict, Any, Optional, List, Union

import openai
from openai import OpenAI

from ..errors import APIError
from .logging import get_logger
from .paths import ensure_dir

logger = get_logger(__name__)

class OpenAIClient:
    """Client for OpenAI API."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        cache_dir: Optional[Union[str, Path]] = None
    ):
        """Initialize OpenAI client.
        
        Args:
            api_key: Optional API key (defaults to OPENAI_API_KEY env var)
            cache_dir: Optional cache directory
        """
        # Set API key
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise APIError("OpenAI API key not found")
        
        # Initialize client
        self.client = OpenAI(api_key=self.api_key)
        
        # Set up caching
        self.cache_dir = Path(cache_dir) if cache_dir else None
        if self.cache_dir:
            ensure_dir(self.cache_dir)
    
    def _get_cache_path(self, cache_key: str) -> Optional[Path]:
        """Get cache file path.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cache file path or None if caching disabled
        """
        if not self.cache_dir:
            return None
            
        return self.cache_dir / f"{cache_key}.json"
    
    def _load_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Load result from cache.
        
        Args:
            cache_key: Cache key
            
        Returns:
            Cached result or None if not found
        """
        import json
        
        cache_path = self._get_cache_path(cache_key)
        if not cache_path or not cache_path.exists():
            return None
            
        try:
            return json.loads(cache_path.read_text())
        except Exception as e:
            logger.warning(f"Failed to load cache: {str(e)}")
            return None
    
    def _save_to_cache(self, cache_key: str, result: Dict[str, Any]) -> None:
        """Save result to cache.
        
        Args:
            cache_key: Cache key
            result: Result to cache
        """
        import json
        
        cache_path = self._get_cache_path(cache_key)
        if not cache_path:
            return
            
        try:
            cache_path.write_text(json.dumps(result, indent=2))
        except Exception as e:
            logger.warning(f"Failed to save cache: {str(e)}")
    
    async def generate_text(
        self,
        prompt: str,
        model: str = "gpt-4",
        max_tokens: int = 1000,
        temperature: float = 0.7,
        cache_key: Optional[str] = None
    ) -> str:
        """Generate text using OpenAI API.
        
        Args:
            prompt: Text prompt
            model: Model to use
            max_tokens: Maximum tokens to generate
            temperature: Sampling temperature
            cache_key: Optional cache key
            
        Returns:
            Generated text
            
        Raises:
            APIError: If API call fails
        """
        try:
            # Check cache
            if cache_key:
                cached = self._load_from_cache(cache_key)
                if cached:
                    return cached['text']
            
            # Call API
            response = await self.client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=max_tokens,
                temperature=temperature
            )
            
            # Extract text
            text = response.choices[0].message.content
            
            # Cache result
            if cache_key:
                self._save_to_cache(cache_key, {'text': text})
            
            return text
            
        except Exception as e:
            raise APIError(f"OpenAI API call failed: {str(e)}")
    
    async def generate_image_description(
        self,
        image_path: Union[str, Path],
        model: str = "gpt-4-vision-preview",
        max_tokens: int = 300,
        cache_key: Optional[str] = None
    ) -> str:
        """Generate description for image using OpenAI API.
        
        Args:
            image_path: Path to image file
            model: Model to use
            max_tokens: Maximum tokens to generate
            cache_key: Optional cache key
            
        Returns:
            Generated description
            
        Raises:
            APIError: If API call fails
        """
        try:
            # Check cache
            if cache_key:
                cached = self._load_from_cache(cache_key)
                if cached:
                    return cached['description']
            
            # Read image
            image_path = Path(image_path)
            if not image_path.exists():
                raise APIError(f"Image not found: {image_path}")
            
            # Call API
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please describe this image in detail."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_path.read_bytes()}"
                                }
                            }
                        ]
                    }
                ],
                max_tokens=max_tokens
            )
            
            # Extract description
            description = response.choices[0].message.content
            
            # Cache result
            if cache_key:
                self._save_to_cache(cache_key, {'description': description})
            
            return description
            
        except Exception as e:
            raise APIError(f"OpenAI API call failed: {str(e)}")
    
    async def analyze_code(
        self,
        code: str,
        model: str = "gpt-4",
        max_tokens: int = 500,
        cache_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """Analyze code using OpenAI API.
        
        Args:
            code: Code to analyze
            model: Model to use
            max_tokens: Maximum tokens to generate
            cache_key: Optional cache key
            
        Returns:
            Dict containing analysis results
            
        Raises:
            APIError: If API call fails
        """
        try:
            # Check cache
            if cache_key:
                cached = self._load_from_cache(cache_key)
                if cached:
                    return cached['analysis']
            
            # Call API
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": (
                            "Please analyze this code and provide:\n"
                            "1. A brief description\n"
                            "2. Key functions and their purposes\n"
                            "3. Potential improvements\n\n"
                            f"{code}"
                        )
                    }
                ],
                max_tokens=max_tokens
            )
            
            # Extract analysis
            analysis = {
                'text': response.choices[0].message.content,
                'model': model,
                'tokens': response.usage.total_tokens
            }
            
            # Cache result
            if cache_key:
                self._save_to_cache(cache_key, {'analysis': analysis})
            
            return analysis
            
        except Exception as e:
            raise APIError(f"OpenAI API call failed: {str(e)}")
    
    async def summarize_text(
        self,
        text: str,
        model: str = "gpt-4",
        max_tokens: int = 300,
        cache_key: Optional[str] = None
    ) -> str:
        """Summarize text using OpenAI API.
        
        Args:
            text: Text to summarize
            model: Model to use
            max_tokens: Maximum tokens to generate
            cache_key: Optional cache key
            
        Returns:
            Generated summary
            
        Raises:
            APIError: If API call fails
        """
        try:
            # Check cache
            if cache_key:
                cached = self._load_from_cache(cache_key)
                if cached:
                    return cached['summary']
            
            # Call API
            response = await self.client.chat.completions.create(
                model=model,
                messages=[
                    {
                        "role": "user",
                        "content": f"Please summarize this text:\n\n{text}"
                    }
                ],
                max_tokens=max_tokens
            )
            
            # Extract summary
            summary = response.choices[0].message.content
            
            # Cache result
            if cache_key:
                self._save_to_cache(cache_key, {'summary': summary})
            
            return summary
            
        except Exception as e:
            raise APIError(f"OpenAI API call failed: {str(e)}")
    
    def clear_cache(self) -> None:
        """Clear API response cache."""
        if not self.cache_dir:
            return
            
        try:
            for cache_file in self.cache_dir.glob("*.json"):
                cache_file.unlink()
        except Exception as e:
            logger.warning(f"Failed to clear cache: {str(e)}") 