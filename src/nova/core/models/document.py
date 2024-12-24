"""Data models for Nova processor configuration."""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import (
    BaseModel, 
    Field, 
    ConfigDict,
    model_validator
)
from pydantic.types import conint, confloat
from typing_extensions import Annotated
import re

from .retry import RetryConfig

# Custom string types
class ApiKeyStr(str):
    """OpenAI API key string type."""
    @classmethod
    def __get_validators__(cls):
        yield cls.validate

    @classmethod
    def validate(cls, v: str) -> str:
        """Validate API key string."""
        if not isinstance(v, str):
            raise TypeError("API key must be a string")
        
        # Allow default value during testing
        if v == "${OPENAI_API_KEY}":
            return v
            
        # Validate real API key
        if not re.match(r'^sk-[A-Za-z0-9]{48}$', v):
            raise ValueError("Invalid API key format")
        return v

ModelNameStr = Annotated[str, Field(pattern=r'^gpt-4-vision-preview|gpt-4$')]
LogLevelStr = Annotated[str, Field(pattern=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$')]
ImageFormatStr = Annotated[str, Field(pattern=r'^(png|jpe?g|gif|webp|heic)$')]
OutputFormatStr = Annotated[str, Field(pattern=r'^(PNG|JPEG|WEBP)$')]
FileExtStr = Annotated[str, Field(pattern=r'^\.[a-zA-Z0-9]+$')]
CircularRefStr = Annotated[str, Field(pattern=r'^(error|warn|ignore)$')]

class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""
    api_key: ApiKeyStr = Field(default="${OPENAI_API_KEY}")
    model: ModelNameStr = "gpt-4-vision-preview"
    enabled: bool = True
    max_tokens: conint(ge=1, le=4096) = 300
    temperature: confloat(ge=0.0, le=2.0) = 0.7
    retry: RetryConfig = RetryConfig()

    @model_validator(mode='after')
    def validate_api_key(self) -> 'OpenAIConfig':
        """Validate API key."""
        # During testing, allow the default API key
        if self.enabled and self.api_key == "${OPENAI_API_KEY}":
            self.enabled = False  # Disable OpenAI integration if no key is provided
        return self

class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = True
    max_size: conint(ge=1024*1024) = 1024 * 1024 * 1000  # 1GB
    max_age: conint(ge=60) = 60 * 60 * 24 * 30  # 30 days
    cleanup_interval: conint(ge=60) = 60 * 60  # 1 hour

    @model_validator(mode='after')
    def validate_cache_config(self) -> 'CacheConfig':
        """Validate cache configuration."""
        if self.cleanup_interval > self.max_age:
            raise ValueError("cleanup_interval must be less than max_age")
        return self

class ImageConfig(BaseModel):
    """Image processing configuration."""
    formats: List[ImageFormatStr] = [
        "png", "jpg", "jpeg", "gif", "webp", "heic"
    ]
    output_format: OutputFormatStr = "JPEG"
    quality: conint(ge=1, le=100) = 85
    max_size: conint(ge=1024) = Field(
        default=1024 * 1024 * 10,  # 10MB
        description="Maximum allowed image size in bytes"
    )
    openai: OpenAIConfig = OpenAIConfig()
    cache: CacheConfig = CacheConfig()

    @model_validator(mode='after')
    def validate_unique_formats(self) -> 'ImageConfig':
        """Validate image formats."""
        unique_formats = set(self.formats)
        if len(unique_formats) != len(self.formats):
            raise ValueError("Image formats must be unique")
        return self

class EmbedConfig(BaseModel):
    """Embed handling configuration."""
    enabled: bool = True
    max_depth: conint(ge=1, le=10) = 3
    circular_refs: CircularRefStr = "error"
    allow_external: bool = False
    max_size: conint(ge=1024) = 1024 * 1024  # 1MB

class MarkdownConfig(BaseModel):
    """Markdown processing configuration."""
    extensions: List[FileExtStr] = [".md", ".markdown"]
    image_handling: Dict[str, bool] = {
        "copy_images": True,
        "update_paths": True,
        "generate_descriptions": True
    }
    embed_handling: EmbedConfig = EmbedConfig()

    @model_validator(mode='after')
    def validate_extensions(self) -> 'MarkdownConfig':
        """Validate markdown extensions."""
        unique_extensions = set(self.extensions)
        if len(unique_extensions) != len(self.extensions):
            raise ValueError("Markdown extensions must be unique")
        return self

class OfficeConfig(BaseModel):
    """Office document processing configuration."""
    formats: Dict[str, List[str]] = {
        "documents": [".docx", ".doc"],
        "presentations": [".pptx", ".ppt"],
        "spreadsheets": [".xlsx", ".xls"],
        "pdf": [".pdf"]
    }
    extraction: Dict[str, Any] = {
        "preserve_formatting": True,
        "extract_images": True,
        "image_folder": "${processing_dir}/images/original"
    }
    image_extraction: Dict[str, bool] = {
        "process_embedded": True,
        "maintain_links": True
    }

    @model_validator(mode='after')
    def validate_formats(self) -> 'OfficeConfig':
        """Validate office formats."""
        for category, extensions in self.formats.items():
            unique_extensions = set(extensions)
            if len(unique_extensions) != len(extensions):
                raise ValueError(f"Office {category} extensions must be unique")
        return self

class PathsConfig(BaseModel):
    """Configuration for file paths."""
    
    base_dir: str
    input_dir: str
    output_dir: str
    processing_dir: str
    temp_dir: str
    state_dir: str
    phase_dirs: Dict[str, str]
    image_dirs: Dict[str, str]
    office_dirs: Dict[str, str]
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid',
        from_attributes=True
    )
    
    def __init__(self, **data):
        """Initialize PathsConfig."""
        super().__init__(**data)
        
    def model_dump(self) -> Dict[str, Any]:
        """Convert model to dictionary."""
        return {
            'base_dir': str(self.base_dir),
            'input_dir': str(self.input_dir),
            'output_dir': str(self.output_dir),
            'processing_dir': str(self.processing_dir),
            'temp_dir': str(self.temp_dir),
            'state_dir': str(self.state_dir),
            'phase_dirs': {k: str(v) for k, v in self.phase_dirs.items()},
            'image_dirs': {k: str(v) for k, v in self.image_dirs.items()},
            'office_dirs': {k: str(v) for k, v in self.office_dirs.items()}
        }

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: LogLevelStr = Field(default="${NOVA_LOG_LEVEL:-INFO}")
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: Dict[str, Dict[str, Any]] = {
        "console": {
            "class": "logging.StreamHandler",
            "level": "INFO",
            "formatter": "default"
        }
    }

    @model_validator(mode='after')
    def validate_handlers(self) -> 'LoggingConfig':
        """Validate logging handlers."""
        for handler_name, handler_config in self.handlers.items():
            if "class" not in handler_config:
                raise ValueError(f"Handler {handler_name} must have a class")
            if "level" not in handler_config:
                raise ValueError(f"Handler {handler_name} must have a level")
        return self

class ProcessorConfig(BaseModel):
    """Base configuration for processors."""
    
    enabled: bool = True
    processor: str = ""
    output_dir: str = "output"
    options: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid',
        from_attributes=True
    )
    
    def __init__(self, **data):
        """Initialize ProcessorConfig."""
        if 'options' not in data:
            data['options'] = {}
        super().__init__(**data)

class NovaConfig(BaseModel):
    """Main configuration model."""
    paths: PathsConfig
    processors: ProcessorConfig = ProcessorConfig()
    logging: LoggingConfig = LoggingConfig()
    openai: OpenAIConfig = OpenAIConfig()

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra="forbid"
    )