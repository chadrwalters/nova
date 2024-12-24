import pytest
from pathlib import Path
from nova.core.models import LoggingConfig, PathsConfig
from nova.core.config import (
    NovaConfig, ProcessorConfig, MarkdownConfig, ImageConfig, OfficeConfig,
    OpenAIConfig, RetryConfig, CacheConfig, EmbedConfig
)

@pytest.fixture
def processor_config():
    """Create a test ProcessorConfig instance."""
    return ProcessorConfig(
        enabled=True,
        markdown=MarkdownConfig(
            extensions=['.md', '.markdown'],
            image_handling={
                'copy_images': True,
                'update_paths': True,
                'generate_descriptions': True
            },
            embed_handling=EmbedConfig(
                enabled=True,
                max_depth=3,
                circular_refs='error',
                allow_external=False,
                max_size=1024 * 1024
            )
        ),
        image=ImageConfig(
            formats=['png', 'jpg', 'jpeg', 'gif', 'webp', 'heic'],
            output_format='JPEG',
            quality=85,
            max_size=1024 * 1024 * 10,
            openai=OpenAIConfig(
                api_key='${OPENAI_API_KEY}',
                model='gpt-4-vision-preview',
                enabled=True,
                max_tokens=300,
                temperature=0.7,
                retry=RetryConfig(
                    max_attempts=3,
                    initial_delay=1.0,
                    max_delay=10.0,
                    exponential_base=2.0,
                    jitter=True,
                    jitter_factor=0.1
                )
            ),
            cache=CacheConfig(
                enabled=True,
                max_size=1024 * 1024 * 1000,
                max_age=60 * 60 * 24 * 30,
                cleanup_interval=60 * 60
            )
        ),
        office=OfficeConfig(
            formats={
                'documents': ['.docx', '.doc'],
                'presentations': ['.pptx', '.ppt'],
                'spreadsheets': ['.xlsx', '.xls'],
                'pdf': ['.pdf']
            },
            extraction={
                'preserve_formatting': True,
                'extract_images': True,
                'image_folder': '${processing_dir}/images/original'
            },
            image_extraction={
                'process_embedded': True,
                'maintain_links': True
            }
        )
    )

@pytest.fixture
def nova_config(tmp_path):
    """Create a test NovaConfig instance."""
    paths_config = PathsConfig(
        base_dir=str(tmp_path),
        input_dir=str(tmp_path / 'input'),
        output_dir=str(tmp_path / 'output'),
        processing_dir=str(tmp_path / 'processing'),
        temp_dir=str(tmp_path / 'temp'),
        state_dir=str(tmp_path / 'state'),
        phase_dirs={
            'markdown_parse': str(tmp_path / 'phase' / 'markdown_parse'),
            'markdown_consolidate': str(tmp_path / 'phase' / 'markdown_consolidate'),
            'markdown_aggregate': str(tmp_path / 'phase' / 'markdown_aggregate'),
            'markdown_split': str(tmp_path / 'phase' / 'markdown_split')
        },
        image_dirs={
            'original': str(tmp_path / 'images' / 'original'),
            'processed': str(tmp_path / 'images' / 'processed'),
            'metadata': str(tmp_path / 'images' / 'metadata'),
            'cache': str(tmp_path / 'images' / 'cache')
        },
        office_dirs={
            'assets': str(tmp_path / 'office' / 'assets'),
            'temp': str(tmp_path / 'office' / 'temp')
        }
    )

    # Create processor config
    processor_config = {
        'markdown': MarkdownConfig(
            extensions=['.md', '.markdown'],
            image_handling={
                'copy_images': True,
                'update_paths': True,
                'generate_descriptions': True
            },
            embed_handling=EmbedConfig(
                enabled=True,
                max_depth=3,
                circular_refs='error',
                allow_external=False,
                max_size=1024 * 1024
            )
        ),
        'image': ImageConfig(
            formats=['png', 'jpg', 'jpeg', 'gif', 'webp', 'heic'],
            output_format='JPEG',
            quality=85,
            max_size=1024 * 1024 * 10,
            openai=OpenAIConfig(
                api_key='${OPENAI_API_KEY}',
                model='gpt-4-vision-preview',
                enabled=True,
                max_tokens=300,
                temperature=0.7,
                retry=RetryConfig(
                    max_attempts=3,
                    initial_delay=1.0,
                    max_delay=10.0,
                    exponential_base=2.0,
                    jitter=True,
                    jitter_factor=0.1
                )
            ),
            cache=CacheConfig(
                enabled=True,
                max_size=1024 * 1024 * 1000,
                max_age=60 * 60 * 24 * 30,
                cleanup_interval=60 * 60
            )
        ),
        'office': OfficeConfig(
            formats={
                'documents': ['.docx', '.doc'],
                'presentations': ['.pptx', '.ppt'],
                'spreadsheets': ['.xlsx', '.xls'],
                'pdf': ['.pdf']
            },
            extraction={
                'preserve_formatting': True,
                'extract_images': True,
                'image_folder': '${processing_dir}/images/original'
            },
            image_extraction={
                'process_embedded': True,
                'maintain_links': True
            }
        )
    }

    # Create logging config
    logging_config = LoggingConfig(
        level='INFO',
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers={
            'console': {
                'class': 'logging.StreamHandler',
                'level': 'INFO',
                'formatter': 'default'
            }
        }
    )

    return NovaConfig(
        paths=paths_config,
        processors=processor_config,
        logging=logging_config
    )
  