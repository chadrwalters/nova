"""Core models for Nova Document Processor."""

from enum import Enum
from typing import List, Optional
from pathlib import Path
import os
from pydantic import BaseModel, Field

class ErrorTolerance(str, Enum):
    """Error tolerance levels."""
    STRICT = "strict"
    LENIENT = "lenient"

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = Field(default="INFO")
    format: str = Field(default="json")
    filter_binary: bool = Field(default=True)
    max_binary_length: int = Field(default=100)

class MarkdownConfig(BaseModel):
    """Markdown processing configuration."""
    typographer: bool = Field(default=True)
    linkify: bool = Field(default=True)
    breaks: bool = Field(default=True)
    plugins: List[str] = Field(
        default=["table", "strikethrough", "taskList", "linkify", "image"]
    )

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
            raise ValueError("NOVA_PROCESSING_DIR environment variable not set")
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

class ProcessingConfig(BaseModel):
    """Processing configuration."""
    error_tolerance: ErrorTolerance = Field(default=ErrorTolerance.LENIENT)
    max_retries: int = Field(default=3)
    max_file_size: int = Field(default=10)  # MB
    max_total_size: int = Field(default=50)  # MB

class OfficeConfig(BaseModel):
    """Office document conversion configuration."""
    preserve_images: bool = Field(default=True)
    ocr_enabled: bool = Field(default=True)
    max_image_size: int = Field(default=5242880)  # 5MB

class NovaConfig(BaseModel):
    """Configuration for Nova Document Processor."""
    processing: ProcessingConfig = Field(default_factory=ProcessingConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    markdown: MarkdownConfig = Field(default_factory=MarkdownConfig)
    office: OfficeConfig = Field(default_factory=OfficeConfig)
    image: ImageProcessingConfig = Field(default_factory=ImageProcessingConfig)