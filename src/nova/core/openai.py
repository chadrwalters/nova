"""OpenAI integration module for Nova document processor."""

import os
from typing import Optional
from openai import OpenAI, OpenAIError

from .errors import ConfigurationError
from .logging import get_logger

logger = get_logger(__name__)

def setup_openai_client() -> Optional[OpenAI]:
    """Initialize OpenAI client with proper error handling."""
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not openai_key:
        logger.warning("OpenAI API key not found in environment variable OPENAI_API_KEY")
        return None
        
    try:
        client = OpenAI(api_key=openai_key)
        
        # Test the client with a minimal request
        response = client.chat.completions.create(
            model="gpt-4-turbo-2024-04-09",
            messages=[{
                "role": "user",
                "content": "Test connection"
            }],
            max_tokens=1
        )
        
        logger.info("OpenAI client initialized and tested successfully")
        return client
        
    except OpenAIError as e:
        error_msg = f"OpenAI API error: {str(e)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg)
        
    except Exception as e:
        error_msg = f"Failed to initialize OpenAI client: {str(e)}"
        logger.error(error_msg)
        raise ConfigurationError(error_msg) 