"""Groq API provider for image analysis."""

import asyncio
import base64
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, Optional, Union
import re

from groq import Groq

from ..utils.cache import CacheManager

logger = logging.getLogger(__name__)

class GrokAPIError(Exception):
    """Exception raised for Groq API errors."""
    pass

class GrokProvider:
    """Provider for the Groq API for image description."""
    
    def __init__(self, api_key: Optional[str] = None, cache_dir: Path = None):
        """Initialize the Groq provider with API key and cache directory.
        
        Args:
            api_key: Optional API key (defaults to GROQ_API_KEY env var)
            cache_dir: Optional cache directory (defaults to GROQ_CACHE_DIR env var)
        """
        self.api_key = api_key or os.getenv('GROQ_API_KEY')
        if not self.api_key:
            raise ValueError("Groq API key not provided")
        
        self.cache_dir = cache_dir or os.getenv('GROQ_CACHE_DIR')
        
        # Configure logging for groq client
        groq_logger = logging.getLogger('groq._base_client')
        groq_logger.setLevel(logging.INFO)  # Reduce verbosity
        
        # Add filter for sensitive data
        class GroqLogFilter(logging.Filter):
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
        
        groq_logger.addFilter(GroqLogFilter())
        
        # Initialize client
        self.client = Groq(api_key=self.api_key)
        
        self.base_url = "https://api.groq.com/openai/v1"
        self.max_retries = 3
        self.retry_delay = 1.0
        self.backoff_factor = 2.0
        self.timeout = 30.0
        
        # Initialize cache
        self.cache = CacheManager(self.cache_dir)
    
    async def get_image_description(self, image_path: str) -> str:
        """Get a description of an image using the Groq API."""
        try:
            # Check cache first
            cache_key = self._generate_cache_key(image_path)
            if cached_result := self.cache.get(cache_key):
                return cached_result

            # Prepare image data
            with open(image_path, 'rb') as f:
                image_data = base64.b64encode(f.read()).decode('utf-8')

            # Prepare API request with minimal prompt
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": "This is a screenshot. Please analyze it and provide:\n1. Any visible text content\n2. Description of the UI layout and elements\n3. Key information or data shown\nBe thorough but concise."
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_data}"
                            }
                        }
                    ]
                }
            ]

            # Make API call with retries
            for attempt in range(self.max_retries):
                try:
                    response = await self.client.chat.completions.create(
                        messages=messages,
                        model="mixtral-8x7b-32768",  # Better for OCR and text extraction
                        max_tokens=1024,  # Increased for more detailed analysis
                        temperature=0.2  # Lower for more focused extraction
                    )
                    
                    description = response.choices[0].message.content
                    self.cache.set(cache_key, description)
                    return description
                    
                except Exception as e:
                    error_msg = f"Error code: {getattr(e, 'status_code', 'unknown')} - {str(e)}"
                    logging.warning(f"API call attempt {attempt + 1} failed: {error_msg}")
                    
                    if attempt < self.max_retries - 1:
                        await asyncio.sleep(self.retry_delay * (self.backoff_factor ** attempt))
                    else:
                        raise GrokAPIError(f"Failed to call Groq API: {error_msg}")

        except Exception as e:
            raise GrokAPIError(f"Failed to generate image description: {str(e)}")

    def _generate_cache_key(self, image_path: str) -> str:
        """Generate a cache key for an image."""
        try:
            mtime = os.path.getmtime(image_path)
            return f"{image_path}_{mtime}"
        except OSError:
            return image_path 