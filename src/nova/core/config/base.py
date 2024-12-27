"""Base configuration classes for Nova document processor."""

from typing import Dict, Any, List, Optional, Union
from pydantic import BaseModel, Field, model_validator
from pathlib import Path

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
    """Path configuration."""
    base_dir: str = Field(description="Base directory for all paths")
    input_dir: Optional[str] = Field(None, description="Input directory")
    output_dir: Optional[str] = Field(None, description="Output directory")
    processing_dir: Optional[str] = Field(None, description="Processing directory")
    temp_dir: Optional[str] = Field(None, description="Temporary directory")

class ProcessorConfig(BaseModel):
    """Processor configuration."""
    name: str = Field(description="Processor name")
    description: str = Field(description="Processor description")
    processor: str = Field(description="Processor class name")
    input_dir: Optional[str] = Field(None, description="Input directory")
    output_dir: Optional[str] = Field(None, description="Output directory")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processor options")

class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    input_dir: str = Field(..., description="Input directory path")
    output_dir: str = Field(..., description="Output directory path")
    processing_dir: str = Field(..., description="Processing directory path")
    temp_dir: str = Field(..., description="Temporary directory path")
    cache_dir: Optional[str] = Field(None, description="Cache directory path")
    log_level: str = Field("INFO", description="Logging level")
    phases: Dict[str, Dict[str, Any]] = Field(default_factory=dict, description="Pipeline phases")
    options: Dict[str, Any] = Field(default_factory=dict, description="Pipeline options")

    @model_validator(mode='before')
    @classmethod
    def validate_config(cls, values: Dict[str, Any]) -> Dict[str, Any]:
        """Validate and transform configuration values.
        
        Args:
            values: Configuration dictionary
            
        Returns:
            Validated configuration dictionary
        """
        if not isinstance(values, dict):
            return values

        # Extract paths from nested structure if present
        if 'paths' in values:
            paths = values.pop('paths')
            if isinstance(paths, dict):
                for key, value in paths.items():
                    if key in ['input_dir', 'output_dir', 'processing_dir', 'temp_dir', 'cache_dir']:
                        values[key] = str(value)

        # Ensure required paths are present
        required_paths = ['input_dir', 'output_dir', 'processing_dir', 'temp_dir']
        for path in required_paths:
            if path not in values:
                values[path] = str(Path(f"nova/{path}"))

        # Convert paths to strings
        for key in ['input_dir', 'output_dir', 'processing_dir', 'temp_dir', 'cache_dir']:
            if key in values and values[key] is not None:
                values[key] = str(values[key])

        return values

    def get_input_dir(self) -> Path:
        """Get input directory path.
        
        Returns:
            Input directory path
        """
        return Path(self.input_dir)

    def get_output_dir(self) -> Path:
        """Get output directory path.
        
        Returns:
            Output directory path
        """
        return Path(self.output_dir)

    def get_processing_dir(self) -> Path:
        """Get processing directory path.
        
        Returns:
            Processing directory path
        """
        return Path(self.processing_dir)

    def get_temp_dir(self) -> Path:
        """Get temporary directory path.
        
        Returns:
            Temporary directory path
        """
        return Path(self.temp_dir)

    def get_cache_dir(self) -> Optional[Path]:
        """Get cache directory path.
        
        Returns:
            Cache directory path or None if not set
        """
        return Path(self.cache_dir) if self.cache_dir else None

    def get_phase_config(self, phase_name: str) -> Dict[str, Any]:
        """Get configuration for a phase.
        
        Args:
            phase_name: Name of the phase
            
        Returns:
            Phase configuration dictionary
            
        Raises:
            KeyError: If phase not found
        """
        if phase_name not in self.phases:
            raise KeyError(f"Phase not found: {phase_name}")
        return self.phases[phase_name]

    def get_option(self, key: str, default: Any = None) -> Any:
        """Get pipeline option.
        
        Args:
            key: Option key
            default: Default value if not found
            
        Returns:
            Option value
        """
        return self.options.get(key, default)

    def set_option(self, key: str, value: Any) -> None:
        """Set pipeline option.
        
        Args:
            key: Option key
            value: Option value
        """
        self.options[key] = value

    def update_phase_config(self, phase_name: str, config: Dict[str, Any]) -> None:
        """Update configuration for a phase.
        
        Args:
            phase_name: Name of the phase
            config: Phase configuration dictionary
        """
        if phase_name not in self.phases:
            self.phases[phase_name] = {}
        self.phases[phase_name].update(config)

    @classmethod
    def from_config(cls, config: Dict[str, Any]) -> 'PipelineConfig':
        """Create pipeline configuration from dictionary.
        
        Args:
            config: Configuration dictionary
            
        Returns:
            Pipeline configuration
        """
        return cls(**config)

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