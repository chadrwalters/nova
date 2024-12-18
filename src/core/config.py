"""Configuration management for Nova Document Processor."""

import os
from pathlib import Path
from typing import List, Optional

import yaml
from pydantic import BaseModel, Field

from .errors import ConfigError
from .models import ErrorTolerance, LoggingConfig
from .logging import get_logger

logger = get_logger(__name__)

class ProcessingConfig(BaseModel):
    """Processing configuration."""
    error_tolerance: ErrorTolerance = Field(default=ErrorTolerance.LENIENT)
    max_retries: int = Field(default=3)
    max_file_size: int = Field(default=10)  # MB
    max_total_size: int = Field(default=50)  # MB

class MarkdownConfig(BaseModel):
    """Markdown processing configuration."""
    typographer: bool = Field(default=True)
    linkify: bool = Field(default=True)
    breaks: bool = Field(default=True)
    plugins: List[str] = Field(
        default=["table", "strikethrough", "taskList", "linkify", "image", "footnote"]
    )

class OfficeConfig(BaseModel):
    """Office document conversion configuration."""
    preserve_images: bool = Field(default=True)
    ocr_enabled: bool = Field(default=True)
    max_image_size: int = Field(default=5242880)  # 5MB

class ImageProcessingConfig(BaseModel):
    """Image processing configuration."""
    quality: int = Field(default=85, ge=1, le=100)
    max_width: int = Field(default=1920, gt=0)
    max_height: int = Field(default=1080, gt=0)
    preferred_format: str = Field(default="png")
    cache_enabled: bool = Field(default=True)
    cache_duration: int = Field(default=86400)  # 24 hours in seconds
    retry_attempts: int = Field(default=3, ge=1)
    timeout: int = Field(default=30, gt=0)  # seconds
    
    @property
    def base_dir(self) -> Path:
        """Get base directory for image processing."""
        processing_dir = os.getenv('NOVA_PROCESSING_DIR')
        if not processing_dir:
            raise ConfigError("NOVA_PROCESSING_DIR environment variable not set")
        return Path(processing_dir) / "images"
    
    @property
    def original_dir(self) -> Path:
        """Get directory for original images."""
        return self.base_dir / "originals"
    
    @property
    def processed_dir(self) -> Path:
        """Get directory for processed images."""
        return self.base_dir / "processed"
    
    @property
    def metadata_dir(self) -> Path:
        """Get directory for image metadata."""
        return self.base_dir / "metadata"
    
    @property
    def cache_dir(self) -> Path:
        """Get directory for image cache."""
        return self.base_dir / "cache"

class NovaConfig(BaseModel):
    """Nova configuration."""
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    markdown: MarkdownConfig = Field(default_factory=MarkdownConfig)
    office: OfficeConfig = Field(default_factory=OfficeConfig)
    image: ImageProcessingConfig = Field(default_factory=ImageProcessingConfig)

def load_config(config_path: Optional[str] = None) -> NovaConfig:
    """Load configuration from file."""
    try:
        if config_path is None:
            config_path = Path('config/default_config.yaml')
        else:
            config_path = Path(config_path)
            
        if not config_path.exists():
            raise ConfigError(f"Config file not found: {config_path}")
            
        with open(config_path) as f:
            config_data = yaml.safe_load(f)
            
        return NovaConfig(**config_data)
        
    except Exception as e:
        logger.error("Failed to load config: %s", str(e))
        raise ConfigError(f"Failed to load config: {str(e)}")

# ... rest of config classes ...