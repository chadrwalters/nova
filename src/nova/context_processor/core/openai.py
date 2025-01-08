"""OpenAI client for image analysis."""

import logging
from typing import Optional

from openai import AsyncOpenAI

from ..config.manager import ConfigManager

logger = logging.getLogger(__name__)


class OpenAIClient:
    """Client for OpenAI API interactions."""

    def __init__(self, config: ConfigManager):
        """Initialize OpenAI client.

        Args:
            config: Nova configuration manager
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.apis.openai.api_key)

    async def analyze_image(self, image_base64: str) -> Optional[str]:
        """Analyze an image using OpenAI's vision model.

        Args:
            image_base64: Base64 encoded image data

        Returns:
            Analysis text if successful, None if failed
        """
        try:
            response = await self.client.chat.completions.create(
                model="gpt-4o",  # Using the specified model from rules
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Please analyze this image and provide a detailed description."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ]
            )

            # Extract the analysis from the response
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            
            return None

        except Exception as e:
            logger.error(f"Failed to analyze image with OpenAI: {str(e)}")
            return None 