import pytest
from pathlib import Path
from nova.core.config import NovaConfig, ProcessorConfig

@pytest.fixture
def processor_config():
    """Create a processor config for testing."""
    from nova.core.config import ProcessorConfig
    
    config = {
        'output_files': {
            'summary': 'summary.md',
            'raw_notes': 'raw_notes.md',
            'attachments': 'attachments.md'
        },
        'section_markers': {
            'summary': '--==SUMMARY==--',
            'raw_notes': '--==RAW NOTES==--',
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
    
    return ProcessorConfig(**config)

@pytest.fixture
def nova_config(tmp_path):
    """Create a nova config for testing."""
    from nova.core.config import NovaConfig, PathsConfig
    
    paths_config = PathsConfig(
        base_dir=str(tmp_path),
        input_dir=str(tmp_path / 'input'),
        output_dir=str(tmp_path / 'output'),
        processing_dir=str(tmp_path / 'processing'),
        temp_dir=str(tmp_path / 'temp'),
        state_dir=str(tmp_path / 'state'),
        phase_dirs={
            'markdown_parse': str(tmp_path / 'phases/markdown_parse'),
            'markdown_consolidate': str(tmp_path / 'phases/markdown_consolidate'),
            'markdown_aggregate': str(tmp_path / 'phases/markdown_aggregate'),
            'markdown_split': str(tmp_path / 'phases/markdown_split')
        },
        image_dirs={
            'original': str(tmp_path / 'images/original'),
            'processed': str(tmp_path / 'images/processed'),
            'metadata': str(tmp_path / 'images/metadata'),
            'cache': str(tmp_path / 'images/cache')
        },
        office_dirs={
            'assets': str(tmp_path / 'office/assets'),
            'temp': str(tmp_path / 'office/temp')
        }
    )
    
    return NovaConfig(paths=paths_config) 