"""Configuration settings for Nova."""
from pathlib import Path
from typing import Dict, Optional, List

from pydantic import BaseModel


class CacheConfig(BaseModel):
    """Cache configuration."""
    
    dir: Path
    enabled: bool = True
    ttl: int = 3600  # seconds


class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""
    
    api_key: Optional[str] = None
    model: str = "gpt-4o"
    max_tokens: int = 500
    vision_prompt: str = (
        "Please analyze this image and provide a detailed description. "
        "If it's a screenshot, extract any visible text. "
        "If it's a photograph, describe the scene and key elements. "
        "Focus on what makes this image relevant in a note-taking context."
    )


class APIConfig(BaseModel):
    """API configuration."""
    
    openai: Optional[OpenAIConfig] = None


class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    
    phases: List[str] = ["parse", "split"]


class NovaConfig(BaseModel):
    """Nova configuration."""
    
    base_dir: Path
    input_dir: Path
    output_dir: Path
    processing_dir: Path
    cache: CacheConfig
    apis: Optional[APIConfig] = None
    pipeline: Optional[PipelineConfig] = PipelineConfig()
    
    class Config:
        """Pydantic model configuration."""
        
        arbitrary_types_allowed = True 