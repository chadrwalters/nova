"""OpenAI client for API interactions."""

import os
from typing import Any, Dict, List, Optional
import openai
from openai import OpenAI
import logging

logger = logging.getLogger(__name__)

class OpenAIClient:
    """Client for interacting with OpenAI APIs."""
    
    def __init__(self):
        """Initialize OpenAI client."""
        self.api_key = os.getenv('OPENAI_API_KEY')
        if not self.api_key:
            raise ValueError("OpenAI API key not found in environment variables")
            
        self.client = OpenAI(api_key=self.api_key)
        self._test_connection()
        
    def _test_connection(self) -> None:
        """Test OpenAI API connection."""
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": "Test connection"}],
                max_tokens=5
            )
            logger.info("OpenAI client initialized and tested successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {str(e)}")
            raise
            
    def generate_image_description(self, image_path: str) -> str:
        """Generate description for an image.
        
        Args:
            image_path: Path to image file
            
        Returns:
            Generated description
        """
        try:
            with open(image_path, "rb") as image_file:
                response = self.client.chat.completions.create(
                    model="gpt-4-vision-preview",
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {"type": "text", "text": "Please describe this image in detail."},
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{image_file.read()}"
                                    }
                                }
                            ]
                        }
                    ],
                    max_tokens=300
                )
                
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to generate image description: {str(e)}")
            return "Failed to generate description"
            
    def analyze_text(self, text: str) -> Dict[str, Any]:
        """Analyze text content.
        
        Args:
            text: Text to analyze
            
        Returns:
            Analysis results
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "user",
                        "content": f"Please analyze this text and provide key insights:\n\n{text}"
                    }
                ],
                max_tokens=500
            )
            
            return {
                'analysis': response.choices[0].message.content,
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to analyze text: {str(e)}")
            return {
                'analysis': "Failed to analyze text",
                'success': False,
                'error': str(e)
            }
            
    def summarize_text(self, text: str, max_tokens: int = 200) -> str:
        """Generate a summary of text content.
        
        Args:
            text: Text to summarize
            max_tokens: Maximum tokens in summary
            
        Returns:
            Generated summary
        """
        try:
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {
                        "role": "user",
                        "content": f"Please provide a concise summary of this text:\n\n{text}"
                    }
                ],
                max_tokens=max_tokens
            )
            
            return response.choices[0].message.content
            
        except Exception as e:
            logger.error(f"Failed to summarize text: {str(e)}")
            return "Failed to generate summary" 