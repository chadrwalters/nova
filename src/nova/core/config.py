"""Configuration module for Nova document processor."""

from pathlib import Path
from typing import Dict, Any, Optional, List, Set, Union
from pydantic import BaseModel, Field
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

@dataclass
class NovaConfig:
    """Configuration for Nova."""
    
    def __init__(self, **kwargs) -> None:
        """Initialize the Nova configuration.
        
        Args:
            **kwargs: Configuration options
        """
        paths = kwargs.get('paths', {})
        self.paths = PathsConfig(
            base_dir=paths.get('base_dir', ''),
            input_dir=paths.get('input_dir', ''),
            output_dir=paths.get('output_dir', ''),
            processing_dir=paths.get('processing_dir', ''),
            temp_dir=paths.get('temp_dir', ''),
            state_dir=paths.get('state_dir', '')
        )

class ProcessorConfig:
    """Configuration for a processor."""
    
    def __init__(self, **kwargs) -> None:
        """Initialize the processor configuration.
        
        Args:
            **kwargs: Configuration options
        """
        # Extract options from nested config structure
        if 'options' in kwargs:
            processor_options = kwargs['options'].get('components', {}).get('three_file_split_processor', {}).get('config', {})
        else:
            processor_options = kwargs
            
        # Set configuration attributes
        self.output_files = processor_options.get('output_files', {
            'summary': 'summary.md',
            'raw_notes': 'raw_notes.md',
            'attachments': 'attachments.md'
        })
        
        self.section_markers = processor_options.get('section_markers', {
            'summary': '--==SUMMARY==--',
            'raw_notes': '--==RAW_NOTES==--',
            'attachments': '--==ATTACHMENTS==--'
        })
        
        self.attachment_markers = processor_options.get('attachment_markers', {
            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
            'end': '--==ATTACHMENT_BLOCK_END==--'
        })
        
        self.content_type_rules = processor_options.get('content_type_rules', {
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
        })
        
        self.content_preservation = processor_options.get('content_preservation', {
            'validate_input_size': True,
            'validate_output_size': True,
            'track_content_markers': True,
            'verify_section_integrity': True
        })
        
        self.cross_linking = processor_options.get('cross_linking', True)
        self.preserve_headers = processor_options.get('preserve_headers', True)
        self.enabled = kwargs.get('enabled', True)

class OpenAIConfig(BaseModel):
    """Configuration for OpenAI integration."""
    api_key: Optional[str] = None
    model: str = "gpt-4-vision-preview"
    max_tokens: int = 500
    temperature: float = 0.7
    detail_level: str = "high"

class MarkdownConfig(ProcessorConfig):
    """Configuration for markdown processor."""
    extensions: List[str] = [".md", ".markdown"]
    image_handling: Dict[str, bool] = {
        "copy_images": True,
        "update_paths": True
    }
    typographer: bool = True
    aggregate: Dict[str, Any] = {
        "enabled": True,
        "output_filename": "all_merged_markdown.md",
        "include_file_headers": True,
        "add_separators": True
    }
    options: Dict[str, Any] = {
        "components": {
            "consolidate_processor": {
                "config": {
                    "group_by_root": True,
                    "handle_attachments": True,
                    "preserve_structure": True,
                    "attachment_markers": {
                        "start": "--==ATTACHMENT_BLOCK: {filename}==--",
                        "end": "--==ATTACHMENT_BLOCK_END==--"
                    }
                }
            }
        }
    }

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
    """Main configuration model."""
    paths: PathsConfig
    processors: Dict[str, ProcessorConfig] = Field(default_factory=dict)
    openai: OpenAIConfig = Field(default_factory=OpenAIConfig)

    class Config:
        """Pydantic config."""
        arbitrary_types_allowed = True

    @classmethod
    def from_env(cls, paths: 'NovaPaths') -> 'NovaConfig':
        """Create NovaConfig from environment."""
        return cls(
            paths=PathsConfig.from_nova_paths(paths),
            processors={
                'markdown': MarkdownConfig(enabled=True),
                'image': ImageConfig(enabled=True),
                'office': OfficeConfig(enabled=True),
                'three_file_split': ThreeFileSplitConfig(enabled=True)
            },
            openai=OpenAIConfig(
                api_key=os.getenv('OPENAI_API_KEY'),
                model=os.getenv('OPENAI_MODEL', 'gpt-4-vision-preview'),
                max_tokens=int(os.getenv('OPENAI_MAX_TOKENS', '500')),
                temperature=float(os.getenv('OPENAI_TEMPERATURE', '0.7')),
                detail_level=os.getenv('OPENAI_DETAIL_LEVEL', 'high')
            )
        )