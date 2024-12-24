"""Performance tests for the processing pipeline."""

import pytest
import time
import psutil
import concurrent.futures
from pathlib import Path
from typing import Dict, Any

from nova.processors.three_file_split_processor import ThreeFileSplitProcessor
from nova.core.config import ProcessorConfig, NovaConfig, PathsConfig, RetryConfig
from nova.core.config import MarkdownConfig, EmbedConfig, ImageConfig, OpenAIConfig, CacheConfig, OfficeConfig
from nova.core.errors import ProcessingError
from nova.core.logging import get_logger

logger = get_logger(__name__)

@pytest.fixture
def large_content():
    """Create large test content."""
    content_parts = []
    for i in range(1000):  # 1000 sections
        content_parts.extend([
            f"# Section {i}",
            "Regular content " * 100,  # 100 words per section
            f"--==ATTACHMENT_BLOCK: file{i}.txt==--",
            "Attachment content " * 100,  # 100 words per attachment
            "--==ATTACHMENT_BLOCK_END==--",
            "More content " * 100  # 100 more words
        ])
    return "\n\n".join(content_parts)

@pytest.fixture
def processor_config():
    """Create a processor config for testing."""
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
    return NovaConfig(paths=paths_config)

@pytest.fixture
def split_processor(processor_config, nova_config):
    """Create a split processor instance."""
    return ThreeFileSplitProcessor(processor_config, nova_config)

def test_large_file_processing(split_processor, large_content, tmp_path):
    """Test processing of large files."""
    # Set up output files
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Process content and measure time
    start_time = time.time()
    metrics = split_processor.process(large_content, output_files)
    processing_time = time.time() - start_time
    
    # Check processing time
    assert processing_time < 60  # Should process within 60 seconds
    
    # Check file sizes
    total_size = sum(f.stat().st_size for f in output_files.values())
    assert total_size > 0
    assert metrics['total_size'] == total_size
    
    # Check content distribution
    distribution = metrics['distribution']
    assert 20 <= distribution['summary'] <= 40  # Summary should be 20-40%
    assert 40 <= distribution['raw_notes'] <= 60  # Raw notes should be 40-60%
    assert 5 <= distribution['attachments'] <= 20  # Attachments should be 5-20%

def test_memory_usage(split_processor, large_content, tmp_path):
    """Test memory usage during processing."""
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Get initial memory usage
    process = psutil.Process()
    initial_memory = process.memory_info().rss
    
    # Process content
    metrics = split_processor.process(large_content, output_files)
    
    # Get peak memory usage
    peak_memory = metrics['memory_usage']
    
    # Check memory usage
    memory_increase = peak_memory - initial_memory
    assert memory_increase < 1024 * 1024 * 1024  # Should use less than 1GB additional memory

def test_processing_time(split_processor, tmp_path):
    """Test processing time with different file sizes."""
    sizes = [10, 100, 1000]  # Number of sections
    times = []
    
    for size in sizes:
        # Create content of different sizes
        content_parts = []
        for i in range(size):
            content_parts.extend([
                f"# Section {i}",
                "Content " * 10,
                f"--==ATTACHMENT_BLOCK: file{i}.txt==--",
                "Attachment " * 10,
                "--==ATTACHMENT_BLOCK_END==--"
            ])
        content = "\n\n".join(content_parts)
        
        # Set up output files
        output_files = {
            'summary': tmp_path / f'summary_{size}.md',
            'raw_notes': tmp_path / f'raw_notes_{size}.md',
            'attachments': tmp_path / f'attachments_{size}.md'
        }
        
        # Process and measure time
        start_time = time.time()
        split_processor.process(content, output_files)
        times.append(time.time() - start_time)
    
    # Check processing time scaling
    # Time should increase less than linearly with size
    assert times[1] < times[0] * 15  # 100 sections vs 10 sections
    assert times[2] < times[1] * 15  # 1000 sections vs 100 sections

def test_concurrent_processing(tmp_path, processor_config, nova_config):
    """Test concurrent processing of multiple files."""
    num_files = 4
    contents = []
    output_files_list = []

    # Create test data
    for i in range(num_files):
        content_parts = []
        for j in range(100):  # 100 sections per file
            content_parts.extend([
                f"# Section {j}",
                "Content " * 10,
                f"--==ATTACHMENT_BLOCK: file{j}.txt==--",
                "Attachment " * 10,
                "--==ATTACHMENT_BLOCK_END==--"
            ])
        contents.append("\n\n".join(content_parts))

        output_files_list.append({
            'summary': tmp_path / f'summary_{i}.md',
            'raw_notes': tmp_path / f'raw_notes_{i}.md',
            'attachments': tmp_path / f'attachments_{i}.md'
        })

    # Process files concurrently
    start_time = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
        futures = []
        for i in range(num_files):
            processor = ThreeFileSplitProcessor(processor_config, nova_config)
            input_file = tmp_path / f'input_{i}.md'
            input_file.write_text(contents[i])
            futures.append(executor.submit(
                processor.process,
                input_file,
                output_files_list[i]
            ))

        # Wait for all tasks to complete
        concurrent.futures.wait(futures)

    end_time = time.time()
    processing_time = end_time - start_time

    # Verify results
    for i in range(num_files):
        assert (tmp_path / f'summary_{i}.md').exists()
        assert (tmp_path / f'raw_notes_{i}.md').exists()
        assert (tmp_path / f'attachments_{i}.md').exists()

    # Verify processing time is reasonable
    assert processing_time < 10.0  # Should complete in under 10 seconds

def test_incremental_memory_usage(split_processor, tmp_path):
    """Test memory usage with incrementally larger content."""
    base_size = 1000  # Base content size
    memory_usages = []
    
    for multiplier in [1, 2, 4, 8]:
        # Create content
        size = base_size * multiplier
        content_parts = []
        for i in range(size):
            content_parts.extend([
                f"# Section {i}",
                "Content " * 5,
                f"--==ATTACHMENT_BLOCK: file{i}.txt==--",
                "Attachment " * 5,
                "--==ATTACHMENT_BLOCK_END==--"
            ])
        content = "\n\n".join(content_parts)
        
        # Set up output files
        output_files = {
            'summary': tmp_path / f'summary_{size}.md',
            'raw_notes': tmp_path / f'raw_notes_{size}.md',
            'attachments': tmp_path / f'attachments_{size}.md'
        }
        
        # Process and record memory usage
        metrics = split_processor.process(content, output_files)
        memory_usages.append(metrics['memory_usage'])
    
    # Check memory scaling
    # Memory usage should scale sub-linearly with content size
    for i in range(1, len(memory_usages)):
        ratio = memory_usages[i] / memory_usages[i-1]
        assert ratio < 2.0  # Memory should grow less than 2x when content doubles 