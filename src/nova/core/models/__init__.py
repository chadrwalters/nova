"""Core models for Nova document processor."""

# Standard library imports
from pathlib import Path
from typing import Dict, Any, List, Optional, Annotated

# Third-party imports
from pydantic import BaseModel, Field, ConfigDict

# Nova package imports
from nova.core.config.base import PathConfig
from nova.core.config.cache import CacheConfig
from nova.core.config.logging import LoggingConfig
from nova.core.config.openai import OpenAIConfig
from nova.core.config.processor import ProcessorConfig
from nova.core.config.retry import RetryConfig
from nova.core.models.document import Document

__all__ = [
    'Document',
    'NovaConfig',
    'EmbedConfig'
]

class EmbedConfig(BaseModel):
    """Configuration for embeddings."""
    enabled: bool = Field(default=True, description="Whether embeddings are enabled")
    model: str = Field(default="text-embedding-ada-002", description="OpenAI embedding model to use")
    batch_size: int = Field(default=100, description="Number of texts to embed in one batch")
    cache_dir: Optional[Path] = Field(default=None, description="Directory to cache embeddings")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

class NovaConfig(BaseModel):
    """Global Nova configuration."""
    paths: PathConfig = Field(
        default_factory=PathConfig,
        description="Path configuration"
    )
    processors: Dict[str, ProcessorConfig] = Field(
        default_factory=dict,
        description="Processor configurations"
    )
    logging: LoggingConfig = Field(
        default_factory=LoggingConfig,
        description="Logging configuration"
    )
    openai: OpenAIConfig = Field(
        default_factory=OpenAIConfig,
        description="OpenAI configuration"
    )
    retry: RetryConfig = Field(
        default_factory=RetryConfig,
        description="Global retry configuration"
    )
    cache: CacheConfig = Field(
        default_factory=CacheConfig,
        description="Global cache configuration"
    )

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )
