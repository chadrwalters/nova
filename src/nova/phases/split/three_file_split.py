"""Configuration for ThreeFileSplitProcessor."""

from typing import Dict, Any, List
from pydantic import ConfigDict, Field

from ...core.config import ProcessorConfig

class ThreeFileSplitConfig(ProcessorConfig):
    """Configuration for ThreeFileSplitProcessor."""
    
    enabled: bool = True
    processor: str = "ThreeFileSplitProcessor"
    output_dir: str = "output"
    options: Dict[str, Any] = Field(
        default_factory=lambda: {
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
    )
    
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        validate_assignment=True,
        extra='forbid',
        from_attributes=True
    )
    
    def __init__(self, **data):
        """Initialize ThreeFileSplitConfig."""
        # Remove name field if present as it's not part of our schema
        if 'name' in data:
            del data['name']
        super().__init__(**data)
        
    def validate_options(self) -> List[str]:
        """Validate processor options."""
        errors = super().validate_options()
        if not self.enabled:
            return errors
            
        # Validate required components
        if 'components' not in self.options:
            errors.append("Missing required 'components' section in options")
            return errors
            
        components = self.options['components']
        if 'three_file_split_processor' not in components:
            errors.append("Missing required 'three_file_split_processor' component")
            return errors
            
        config = components['three_file_split_processor'].get('config', {})
        
        # Validate output files
        if 'output_files' not in config:
            errors.append("Missing required 'output_files' configuration")
        else:
            required_files = ['summary', 'raw_notes', 'attachments']
            for file_type in required_files:
                if file_type not in config['output_files']:
                    errors.append(f"Missing required output file type: {file_type}")
                    
        # Validate section markers
        if 'section_markers' not in config:
            errors.append("Missing required 'section_markers' configuration")
        else:
            required_markers = ['summary', 'raw_notes', 'attachments']
            for marker_type in required_markers:
                if marker_type not in config['section_markers']:
                    errors.append(f"Missing required section marker: {marker_type}")
                    
        # Validate attachment markers
        if 'attachment_markers' not in config:
            errors.append("Missing required 'attachment_markers' configuration")
        else:
            required_markers = ['start', 'end']
            for marker_type in required_markers:
                if marker_type not in config['attachment_markers']:
                    errors.append(f"Missing required attachment marker: {marker_type}")
                    
        return errors 