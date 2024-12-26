"""Base configuration classes for Nova document processor."""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field

class HandlerConfig(BaseModel):
    """Configuration for a handler component."""
    type: str
    base_handler: Optional[str] = "nova.phases.core.base_handler.BaseHandler"
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    document_conversion: Optional[bool] = False
    image_processing: Optional[bool] = False
    metadata_preservation: Optional[bool] = False
    sort_by_date: Optional[bool] = False
    preserve_headers: Optional[bool] = False
    copy_attachments: Optional[bool] = False
    update_references: Optional[bool] = False
    merge_content: Optional[bool] = False
    section_markers: Optional[Dict[str, str]] = None
    link_style: Optional[str] = None
    position: Optional[str] = None
    add_top_link: Optional[bool] = False
    templates: Optional[Dict[str, Dict[str, str]]] = None

class ComponentConfig(BaseModel):
    """Configuration for a pipeline component."""
    parser: Optional[str] = None
    config: Optional[Dict[str, Any]] = None
    handlers: Optional[List[HandlerConfig]] = None
    formats: Optional[Union[List[str], Dict[str, Any]]] = None
    operations: Optional[Union[List[Dict[str, Any]], Dict[str, Any]]] = None
    temp_files: Optional[Dict[str, bool]] = None
    content_extraction: Optional[Dict[str, Any]] = None

class PathConfig(BaseModel):
    """Configuration for pipeline paths."""
    base_dir: str

class ProcessorConfig(BaseModel):
    """Configuration for a pipeline processor."""
    name: str
    description: str
    input_dir: Optional[str] = None
    output_dir: str
    processor: str
    enabled: Optional[bool] = True
    components: Optional[Dict[str, ComponentConfig]] = Field(default_factory=dict)
    handlers: Optional[List[HandlerConfig]] = Field(default_factory=list)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)

class PipelineConfig(BaseModel):
    """Configuration for the Nova pipeline."""
    paths: PathConfig
    phases: List[ProcessorConfig]
    components: Optional[Dict[str, ComponentConfig]] = None
    input_dir: str = "${NOVA_INPUT_DIR}"
    output_dir: str = "${NOVA_OUTPUT_DIR}"
    processing_dir: str = "${NOVA_PROCESSING_DIR}"
    temp_dir: str = "${NOVA_TEMP_DIR}"
    enabled: Optional[bool] = True

class RetryConfig(BaseModel):
    """Retry configuration."""
    max_retries: int = 3
    delay_between_retries: float = 1.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_on_errors: Optional[List[str]] = None

class LoggingConfig(BaseModel):
    """Logging configuration."""
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: Optional[Dict[str, Any]] = None
    use_rich: bool = True

class OpenAIConfig(BaseModel):
    """OpenAI configuration."""
    enabled: bool = True
    model: str = "gpt-4-0125-preview"
    max_tokens: int = 500
    temperature: float = 0.7
    retry: Optional[Dict[str, Any]] = None

class CacheConfig(BaseModel):
    """Cache configuration."""
    enabled: bool = True
    max_size: int = 1073741824  # 1GB
    max_age: int = 2592000      # 30 days
    cleanup_interval: int = 3600 # 1 hour

class FormatConfig(BaseModel):
    """Format configuration."""
    extract_text: Optional[bool] = None
    preserve_paragraphs: Optional[bool] = None
    extract_slides: Optional[bool] = None
    include_notes: Optional[bool] = None
    table_format: Optional[bool] = None
    preserve_headers: Optional[bool] = None
    preserve_layout: Optional[bool] = None 