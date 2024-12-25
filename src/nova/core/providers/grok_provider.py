"""xAI API provider for image analysis."""

import asyncio
import base64
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union
import re
import io
from PIL import Image

from openai import AsyncOpenAI

from ..utils.cache import CacheManager

logger = logging.getLogger(__name__)

class GrokAPIError(Exception):
    """Exception raised for xAI API errors."""
    pass

class GrokProvider:
    """Provider for the xAI API for image description."""
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: Path = None):
        """Initialize the xAI provider with API key and cache directory.
        
        Args:
            api_key: Optional API key (defaults to XAI_API_KEY env var)
            cache_dir: Optional cache directory (defaults to XAI_CACHE_DIR env var)
        """
        self.api_key = api_key or os.getenv('XAI_API_KEY')
        if not self.api_key:
            raise ValueError("xAI API key not provided")
        
        self.cache_dir = cache_dir or os.getenv('XAI_CACHE_DIR')
        
        # Configure logging for openai client
        openai_logger = logging.getLogger('openai')
        openai_logger.setLevel(logging.INFO)  # Reduce verbosity
        
        # Add filter for sensitive data
        class APILogFilter(logging.Filter):
            def filter(self, record):
                if hasattr(record, 'msg') and isinstance(record.msg, str):
                    # Redact API key
                    record.msg = re.sub(
                        r'(Authorization: Bearer\s+)[^\s]+',
                        r'\1[REDACTED]',
                        record.msg
                    )
                    # Redact base64 data
                    record.msg = re.sub(
                        r'(\'image_url\': {\'url\': \')[^\']+\'',
                        r'\1[base64 data redacted]\'',
                        record.msg
                    )
                return True
        
        openai_logger.addFilter(APILogFilter())
        
        # Initialize client with xAI base URL
        self.client = AsyncOpenAI(
            api_key=self.api_key,
            base_url="https://api.x.ai/v1"
        )
        
        self.max_retries = 3
        self.retry_delay = 1.0
        self.backoff_factor = 2.0
        self.timeout = 30.0
        
        # Initialize cache
        self.cache = CacheManager(self.cache_dir)
    
    def _resize_image_for_api(self, image_path: str, max_size: int = 800) -> bytes:
        """Resize image to stay within API token limits.
        
        Args:
            image_path: Path to image file
            max_size: Maximum dimension size
            
        Returns:
            Resized image as bytes in JPEG format
        """
        with Image.open(image_path) as img:
            # Convert to RGB if needed
            if img.mode in ('RGBA', 'P'):
                img = img.convert('RGB')
            
            # Calculate new dimensions
            ratio = min(max_size / max(img.size[0], img.size[1]), 1.0)
            new_size = tuple(int(dim * ratio) for dim in img.size)
            
            # Resize if needed
            if ratio < 1.0:
                img = img.resize(new_size, Image.Resampling.LANCZOS)
            
            # Save to bytes
            img_byte_arr = io.BytesIO()
            img.save(img_byte_arr, format='JPEG', quality=85, optimize=True)
            return img_byte_arr.getvalue()
    
    async def get_image_description(self, image_path: str) -> str:
        """Get a description of an image using the xAI API."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(image_path)
            cached_result = self.cache.get(cache_key)
            if cached_result and isinstance(cached_result, dict) and 'description' in cached_result:
                return cached_result['description']

            # Prepare image data (resized to stay within token limits)
            image_data = base64.b64encode(self._resize_image_for_api(image_path)).decode('utf-8')

            # Prepare API request with minimal prompt
            messages = [
                {
                    "role": "user",
                    "content": f"Please analyze this image and provide:\n1. Any visible text content\n2. Description of the UI layout and elements\n3. Key information or data shown\nBe thorough but concise.\n\nImage data: {image_data}"
                }
            ]

            # Make API call with retries
            for attempt in range(self.max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        messages=messages,
                        model="grok-beta",  # Use xAI's Grok model
                        max_tokens=1024,  # Increased for more detailed analysis
                        temperature=0.2  # Lower for more focused extraction
                    )
                    
                    description = response.choices[0].message.content
                    self.cache.set(cache_key, "grok", {'description': description})
                    return description
                    
                except Exception as e:
                    error_msg = f"Error code: {getattr(e, 'status_code', 'unknown')} - {str(e)}"
                    logging.warning(f"API call attempt {attempt + 1} failed: {error_msg}")
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (self.backoff_factor ** attempt))
                    else:
                        raise GrokAPIError(f"Failed to call xAI API: {error_msg}")

        except Exception as e:
            raise GrokAPIError(f"Failed to generate image description: {str(e)}")

    def _generate_cache_key(self, image_path: str) -> str:
        """Generate a cache key for an image."""
        try:
            mtime = os.path.getmtime(image_path)
            return f"{image_path}_{mtime}"
        except OSError:
            return image_path