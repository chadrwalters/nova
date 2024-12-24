"""Configuration module for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Union
from pydantic import BaseModel, Field, ConfigDict
import os
from dataclasses import dataclass

@dataclass
class PathsConfig:
    """Configuration for paths used in Nova."""
    base_dir: Union[str, Path]
    input_dir: Union[str, Path]
    output_dir: Union[str, Path]
    processing_dir: Union[str, Path]
    temp_dir: Union[str, Path]
    state_dir: Union[str, Path]
    phase_dirs: Dict[str, Union[str, Path]]
    image_dirs: Dict[str, Union[str, Path]]
    office_dirs: Dict[str, Union[str, Path]]

    def __post_init__(self):
        """Convert string paths to Path objects."""
        self.base_dir = Path(self.base_dir)
        self.input_dir = Path(self.input_dir)
        self.output_dir = Path(self.output_dir)
        self.processing_dir = Path(self.processing_dir)
        self.temp_dir = Path(self.temp_dir)
        self.state_dir = Path(self.state_dir)
        self.phase_dirs = {k: Path(v) for k, v in self.phase_dirs.items()}
        self.image_dirs = {k: Path(v) for k, v in self.image_dirs.items()}
        self.office_dirs = {k: Path(v) for k, v in self.office_dirs.items()}

class LoggingConfig(BaseModel):
    """Configuration for logging."""

    level: str = "INFO"
    format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    handlers: List[str] = ["console"]
    file: Optional[str] = None
    use_rich: bool = True

class RetryConfig(BaseModel):
    """Configuration for retry behavior."""
    max_attempts: int = 3
    initial_delay: float = 1.0
    max_delay: float = 10.0
    exponential_base: float = 2.0
    jitter: bool = True
    jitter_factor: float = 0.1

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

class CacheConfig(BaseModel):
    """Configuration for caching."""
    enabled: bool = True
    max_size: int = 1024 * 1024 * 1000  # 1GB
    max_age: int = 60 * 60 * 24 * 30  # 30 days
    cleanup_interval: int = 60 * 60  # 1 hour

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

class EmbedConfig(BaseModel):
    """Configuration for embedded content."""
    enabled: bool = True
    max_depth: int = 3
    circular_refs: str = 'error'
    allow_external: bool = False
    max_size: int = 1024 * 1024  # 1MB

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

class OpenAIConfig(BaseModel):
    """Configuration for OpenAI integration."""
    api_key: Optional[str] = Field(default=None)
    model: str = "gpt-4-vision-preview"
    max_tokens: int = 500
    temperature: float = 0.7
    detail_level: str = "high"
    retry: Optional[RetryConfig] = None
    enabled: bool = True

    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

class ProcessorConfig(BaseModel):
    """Base processor configuration."""
    
    enabled: bool = Field(default=True)
    processor: str = Field(default="")
    output_dir: str = Field(default="")
    paths: Optional[PathsConfig] = None
    options: Dict[str, Any] = Field(default_factory=dict)
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

class MarkdownConfig(ProcessorConfig):
    """Markdown processor configuration."""
    
    extensions: List[str] = Field(default_factory=lambda: ['.md', '.markdown'])
    image_handling: Dict[str, bool] = Field(
        default_factory=lambda: {
            'copy_images': True,
            'update_paths': True,
            'generate_descriptions': True
        }
    )
    embed_handling: EmbedConfig = Field(default_factory=EmbedConfig)
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid'
    )

class ImageConfig(ProcessorConfig):
    """Configuration for image processor."""
    formats: List[str] = ["png", "jpg", "jpeg", "gif", "webp"]

class OfficeConfig(ProcessorConfig):
    """Configuration for office processor."""
    formats: Dict[str, List[str]] = {
        "documents": [".docx", ".doc"],
        "presentations": [".pptx", ".ppt"],
        "spreadsheets": [".xlsx", ".xls"],
        "pdf": [".pdf"]
    }

@dataclass
class ThreeFileSplitConfig(ProcessorConfig):
    """Configuration for three file split processor."""
    enabled: bool = True
    processor: str = "ThreeFileSplitProcessor"
    output_dir: str = "output"
    options: Dict[str, Any] = None

    def __post_init__(self):
        """Initialize default values."""
        if self.options is None:
            self.options = {
                'components': {
                    'three_file_split_processor': {
                        'config': {
                            'output_files': {
                                'summary': 'summary.md',
                                'raw_notes': 'raw_notes.md',
                                'attachments': 'attachments.md'
                            },
                            'section_markers': {
                                'summary': '--==SUMMARY==--',
                                'raw_notes': '--==RAW_NOTES==--',
                                'attachments': '--==ATTACHMENTS==--'
                            },
                            'attachment_markers': {
                                'start': '--==ATTACHMENT_BLOCK: {filename}==--',
                                'end': '--==ATTACHMENT_BLOCK_END==--'
                            },
                            'content_type_rules': {
                                'summary': [
                                    'Contains high-level overviews',
                                    'Contains key insights and decisions',
                                    'Contains structured content'
                                ],
                                'raw_notes': [
                                    'Contains detailed notes and logs',
                                    'Contains chronological entries',
                                    'Contains unstructured content'
                                ],
                                'attachments': [
                                    'Contains file references',
                                    'Contains embedded content',
                                    'Contains metadata'
                                ]
                            },
                            'content_preservation': {
                                'validate_input_size': True,
                                'validate_output_size': True,
                                'track_content_markers': True,
                                'verify_section_integrity': True
                            },
                            'cross_linking': True,
                            'preserve_headers': True
                        }
                    }
                }
            }
        # Initialize parent class with values from config
        config = self.options['components']['three_file_split_processor']['config']
        super().__init__(
            output_files=config['output_files'],
            section_markers=config['section_markers'],
            attachment_markers=config['attachment_markers'],
            content_type_rules=config['content_type_rules'],
            content_preservation=config['content_preservation'],
            cross_linking=config['cross_linking'],
            preserve_headers=config['preserve_headers']
        )

class NovaConfig(BaseModel):
    """Configuration for Nova document processor."""
    
    paths: PathsConfig
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid',
        from_attributes=True
    )
    
    def __init__(self, **data):
        """Initialize NovaConfig."""
        if 'paths' in data:
            if isinstance(data['paths'], dict):
                data['paths'] = PathsConfig(**data['paths'])
            elif isinstance(data['paths'], PathsConfig):
                # Convert paths to strings to ensure proper initialization
                paths_dict = {
                    'base_dir': str(data['paths'].base_dir),
                    'input_dir': str(data['paths'].input_dir),
                    'output_dir': str(data['paths'].output_dir),
                    'processing_dir': str(data['paths'].processing_dir),
                    'temp_dir': str(data['paths'].temp_dir),
                    'state_dir': str(data['paths'].state_dir),
                    'phase_dirs': {k: str(v) for k, v in data['paths'].phase_dirs.items()},
                    'image_dirs': {k: str(v) for k, v in data['paths'].image_dirs.items()},
                    'office_dirs': {k: str(v) for k, v in data['paths'].office_dirs.items()}
                }
                data['paths'] = PathsConfig(**paths_dict)
        super().__init__(**data)