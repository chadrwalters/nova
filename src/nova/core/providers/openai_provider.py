from typing import Optional
import logging
import re
import os
from openai import AsyncOpenAI

class OpenAIProvider:
    """Provider for OpenAI API integration."""
    
    def __init__(self, api_key: Optional[str] = None):
        """Initialize OpenAI provider.
        
        Args:
            api_key: Optional API key (defaults to OPENAI_API_KEY env var)
        """
        self.api_key = api_key or os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not provided")
        
        # Configure logging for openai client
        openai_logger = logging.getLogger('openai')
        openai_logger.setLevel(logging.INFO)  # Reduce verbosity
        
        # Add filter for sensitive data
        class OpenAILogFilter(logging.Filter):
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
                        r'(\'image\': \')[^\']+\'',
                        r'\1[base64 data redacted]\'',
                        record.msg
                    )
                return True
        
        openai_logger.addFilter(OpenAILogFilter())
        
        # Initialize client
        self.client = AsyncOpenAI(api_key=self.api_key) 