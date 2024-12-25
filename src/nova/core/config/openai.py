"""OpenAI configuration classes."""

from typing import Dict, Optional, List, Annotated
from pydantic import BaseModel, Field, ConfigDict

from .retry import RetryConfig

class OpenAIConfig(BaseModel):
    """Configuration for OpenAI integration."""
    enabled: bool = Field(default=True, description="Whether OpenAI integration is enabled")
    api_key: Optional[str] = Field(default=None, description="OpenAI API key")
    model: str = Field(default="gpt-4-vision-preview", description="OpenAI model to use")
    max_tokens: Annotated[int, Field(ge=1, le=4096)] = Field(default=1000, description="Maximum tokens per request")
    temperature: Annotated[float, Field(ge=0.0, le=2.0)] = Field(default=0.7, description="Model temperature")
    top_p: Annotated[float, Field(ge=0.0, le=1.0)] = Field(default=1.0, description="Top p")
    frequency_penalty: Annotated[float, Field(ge=-2.0, le=2.0)] = Field(default=0.0, description="Frequency penalty")
    presence_penalty: Annotated[float, Field(ge=-2.0, le=2.0)] = Field(default=0.0, description="Presence penalty")
    retry: RetryConfig = Field(default_factory=RetryConfig, description="Retry configuration")

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    ) 