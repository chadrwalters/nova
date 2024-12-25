"""Base configuration classes for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Union
from pydantic import BaseModel, Field, model_validator, ConfigDict

class LoggingConfig(BaseModel):
    """Logging configuration."""
    
    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: Dict[str, Any] = Field(default_factory=dict)
    use_rich: bool = True

class OpenAIConfig(BaseModel):
    """OpenAI configuration."""
    
    enabled: bool = True
    model: str = "gpt-4-0125-preview"
    max_tokens: int = 500
    temperature: float = 0.7
    retry: Dict[str, Any] = Field(default_factory=dict)

class RetryConfig(BaseModel):
    """Retry configuration."""
    
    max_retries: int = 3
    delay_between_retries: float = 1.0
    backoff_factor: float = 2.0
    jitter: bool = True
    retry_on_errors: List[str] = Field(default_factory=list)

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

class PathConfig(BaseModel):
    """Path configuration."""
    
    base_dir: Path = Field(description="Base directory for all operations")
    
    def create_required_dirs(self) -> None:
        """Create required directories."""
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    model_config = ConfigDict(extra='allow')

class ProcessorConfig(BaseModel):
    """Processor configuration."""
    
    output_dir: Path = Field(description="Output directory for processor")
    options: Dict[str, Any] = Field(default_factory=dict, description="Processor-specific options")
    
    model_config = ConfigDict(extra='allow')

class PipelineConfig(BaseModel):
    """Pipeline configuration."""
    
    paths: PathConfig = Field(description="Path configuration")
    phases: List[str] = Field(default_factory=lambda: [
        "MARKDOWN_PARSE",
        "MARKDOWN_CONSOLIDATE",
        "MARKDOWN_AGGREGATE",
        "MARKDOWN_SPLIT_THREEFILES"
    ], description="List of phases to process")
    options: Dict[str, Any] = Field(default_factory=dict, description="Pipeline-specific options")
    debug: bool = Field(default=False, description="Enable debug mode")
    input_dir: Optional[str] = Field(default=None, description="Input directory path")
    output_dir: Optional[str] = Field(default=None, description="Output directory path")
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='allow'  # Allow extra fields
    )
    
    def __init__(self, **data):
        """Initialize pipeline configuration.
        
        Args:
            **data: Configuration data
        """
        # Convert phases to list if needed
        if 'phases' in data and not isinstance(data['phases'], list):
            if isinstance(data['phases'], dict):
                data['phases'] = list(data['phases'].keys())
            else:
                data['phases'] = list(data['phases'])
        
        # Convert paths to PathConfig if needed
        if 'paths' in data and not isinstance(data['paths'], PathConfig):
            data['paths'] = PathConfig(**data['paths'])
            
        super().__init__(**data) 

class ComponentConfig(BaseModel):
    """Component configuration."""
    
    parser: Optional[str] = None
    config: Dict[str, Any] = Field(default_factory=dict)
    formats: Optional[Union[List[str], Dict[str, Dict[str, Any]]]] = None
    operations: Optional[List[Dict[str, Any]]] = None
    
    @model_validator(mode="before")
    def validate_formats(cls, values):
        """Validate and transform formats field."""
        formats = values.get('formats')
        if formats is None:
            return values
            
        if isinstance(formats, list):
            # Simple list of strings is valid
            if all(isinstance(f, str) for f in formats):
                return values
                
            # Convert list of dicts to dict of dicts
            if all(isinstance(f, dict) for f in formats):
                new_formats = {}
                for fmt in formats:
                    for k, v in fmt.items():
                        new_formats[k] = v
                values['formats'] = new_formats
                
        return values
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='allow'  # Allow extra fields
    ) 