"""Data models for Nova processor configuration."""

from pathlib import Path
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
from pydantic import (
    BaseModel, 
    Field, 
    validator, 
    root_validator,
    constr,
    conint,
    confloat
)

class RetryConfig(BaseModel):
    """Retry configuration for API calls."""
    max_attempts: conint(ge=1, le=10) = 3
    initial_delay: confloat(ge=0.1, le=5.0) = 1.0
    max_delay: confloat(ge=1.0, le=60.0) = 10.0
    exponential_base: confloat(ge=1.1, le=4.0) = 2.0
    jitter: bool = True
    jitter_factor: confloat(ge=0.0, le=0.5) = 0.1

    @root_validator
    def validate_delays(cls, values):
        """Validate delay configurations."""
        if values['initial_delay'] >= values['max_delay']:
            raise ValueError("initial_delay must be less than max_delay")
        return values

class OpenAIConfig(BaseModel):
    """OpenAI API configuration."""
    api_key: constr(min_length=20) = Field(default="${OPENAI_API_KEY}")
    model: constr(regex=r'^gpt-4-vision-preview|gpt-4$') = "gpt-4-vision-preview"
    enabled: bool = True
    max_tokens: conint(ge=1, le=4096) = 300
    temperature: confloat(ge=0.0, le=2.0) = 0.7
    retry: RetryConfig = RetryConfig()

    @validator('api_key')
    def validate_api_key(cls, v):
        """Validate API key format."""
        if not v.startswith("${") and not v.startswith("sk-"):
            raise ValueError("Invalid OpenAI API key format")
        return v

class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = True
    max_size: conint(ge=1024*1024) = 1024 * 1024 * 1000  # 1GB
    max_age: conint(ge=60) = 60 * 60 * 24 * 30  # 30 days
    cleanup_interval: conint(ge=60) = 60 * 60  # 1 hour

    @root_validator
    def validate_cache_config(cls, values):
        """Validate cache configuration."""
        if values['enabled'] and values['max_size'] < 1024 * 1024:
            raise ValueError("Cache max_size must be at least 1MB when enabled")
        return values

class ImageConfig(BaseModel):
    """Image processing configuration."""
    formats: List[constr(regex=r'^(png|jpe?g|gif|webp|heic)$')] = [
        "png", "jpg", "jpeg", "gif", "webp", "heic"
    ]
    output_format: Optional[constr(regex=r'^(PNG|JPEG|WEBP)$')] = None
    quality: conint(ge=1, le=100) = 85
    max_size: conint(ge=1024) = Field(
        default=1024 * 1024 * 10,  # 10MB
        description="Maximum allowed image size in bytes"
    )
    openai: OpenAIConfig = OpenAIConfig()
    cache: CacheConfig = CacheConfig()

    @validator('formats')
    def validate_unique_formats(cls, v):
        """Ensure no duplicate formats."""
        return list(dict.fromkeys(v))

class EmbedConfig(BaseModel):
    """Embed handling configuration."""
    enabled: bool = True
    max_depth: conint(ge=1, le=10) = 3
    circular_refs: constr(regex=r'^(error|warn|ignore)$') = "error"
    allow_external: bool = False
    max_size: conint(ge=1024) = 1024 * 1024  # 1MB

class MarkdownConfig(BaseModel):
    """Markdown processing configuration."""
    extensions: List[constr(regex=r'^\.[a-zA-Z0-9]+$')] = [".md", ".markdown"]
    image_handling: Dict[str, bool] = {
        "copy_images": True,
        "update_paths": True,
        "generate_descriptions": True
    }
    embed_handling: EmbedConfig = EmbedConfig()

    @validator('extensions')
    def validate_extensions(cls, v):
        """Validate markdown extensions."""
        if not any(ext.lower() in ['.md', '.markdown'] for ext in v):
            raise ValueError("Must include at least .md or .markdown extension")
        return v

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
        "enabled": True
    }

    @validator('formats')
    def validate_formats(cls, v):
        """Validate office formats."""
        required_types = {"documents", "presentations", "spreadsheets", "pdf"}
        if not all(type_ in v for type_ in required_types):
            raise ValueError(f"Missing required format types: {required_types - v.keys()}")
        return v

class PathsConfig(BaseModel):
    """Path configuration."""
    base_dir: Path = Field(default=Path("${NOVA_BASE_DIR:-/usr/local/nova}"))
    input_dir: Path = Field(default=Path("${NOVA_INPUT_DIR:-${base_dir}/_NovaInput}"))
    output_dir: Path = Field(default=Path("${NOVA_OUTPUT_DIR:-${base_dir}/_NovaOutput}"))
    processing_dir: Path = Field(default=Path("${NOVA_PROCESSING_DIR:-${base_dir}/_NovaProcessing}"))
    temp_dir: Path = Field(default=Path("${NOVA_TEMP_DIR:-${base_dir}/_NovaTemp}"))
    state_dir: Path = Field(default=Path("${processing_dir}/.state"))
    
    phase_dirs: Dict[str, Path]
    image_dirs: Dict[str, Path]
    office_dirs: Dict[str, Path]

    @validator('*')
    def validate_path_vars(cls, v):
        """Validate path variables."""
        if isinstance(v, Path):
            path_str = str(v)
            if "${" in path_str:
                if "}" not in path_str:
                    raise ValueError(f"Invalid path variable format in {path_str}")
                if not any(var in path_str for var in [
                    "NOVA_BASE_DIR",
                    "NOVA_INPUT_DIR",
                    "NOVA_OUTPUT_DIR",
                    "NOVA_PROCESSING_DIR",
                    "NOVA_TEMP_DIR",
                    "base_dir",
                    "processing_dir"
                ]):
                    raise ValueError(f"Unknown variable in path: {path_str}")
        return v

    @root_validator
    def validate_directory_structure(cls, values):
        """Validate directory structure relationships."""
        base_dir = values.get('base_dir')
        if base_dir:
            for key, path in values.items():
                if key != 'base_dir' and isinstance(path, Path):
                    try:
                        path.relative_to(base_dir)
                    except ValueError:
                        raise ValueError(f"{key} must be within base_dir")
        return values

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: constr(regex=r'^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$') = Field(
        default="${NOVA_LOG_LEVEL:-INFO}"
    )
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: Dict[str, Dict[str, Any]] = {
        "file": {
            "enabled": True,
            "path": "${processing_dir}/nova.log",
            "max_size": 10485760,  # 10MB
            "backup_count": 5
        },
        "console": {
            "enabled": True,
            "color": True
        }
    }

    @validator('handlers')
    def validate_handlers(cls, v):
        """Validate logging handlers."""
        if not any(h.get('enabled', False) for h in v.values()):
            raise ValueError("At least one logging handler must be enabled")
        return v

class ProcessorConfig(BaseModel):
    """Processor configuration."""
    enabled: bool = True
    markdown: MarkdownConfig = MarkdownConfig()
    image: ImageConfig = ImageConfig()
    office: OfficeConfig = OfficeConfig()

class NovaConfig(BaseModel):
    """Main configuration model."""
    paths: PathsConfig
    processors: ProcessorConfig = ProcessorConfig()
    logging: LoggingConfig = LoggingConfig()
    openai: OpenAIConfig = OpenAIConfig()

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True
        validate_assignment = True
        extra = "forbid"