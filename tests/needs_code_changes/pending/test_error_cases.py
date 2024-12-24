"""Error case tests for the processing pipeline."""

import pytest
from pathlib import Path
from typing import Dict, Any

from nova.processors.three_file_split_processor import ThreeFileSplitProcessor
from nova.core.errors import ProcessingError
from nova.core.config import ProcessorConfig, MarkdownConfig, EmbedConfig, ImageConfig, OpenAIConfig, CacheConfig, OfficeConfig, PathsConfig, NovaConfig, RetryConfig
from nova.core.logging import get_logger
from nova.core.models import LoggingConfig, PathsConfig

logger = get_logger(__name__)

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

def test_invalid_input_empty(split_processor, tmp_path):
    """Test processing empty content."""
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Process empty content
    metrics = split_processor.process("", output_files)
    
    # Check that files are created but empty
    assert all(f.exists() for f in output_files.values())
    assert all(f.stat().st_size == 0 for f in output_files.values())
    assert metrics['total_size'] == 0

def test_invalid_input_none(split_processor, tmp_path):
    """Test processing None content."""
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    with pytest.raises(ProcessingError, match="Content cannot be None"):
        split_processor.process(None, output_files)

def test_malformed_content_unclosed_block(split_processor, tmp_path):
    """Test processing content with unclosed attachment block."""
    content = """
# Test Document

--==ATTACHMENT_BLOCK: test.txt==--
Unclosed attachment block
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    with pytest.raises(ProcessingError, match="Unclosed attachment block"):
        split_processor.process(content, output_files)

def test_malformed_content_nested_blocks(split_processor, tmp_path):
    """Test processing content with nested attachment blocks."""
    content = """
# Test Document

--==ATTACHMENT_BLOCK: outer.txt==--
Outer content
--==ATTACHMENT_BLOCK: inner.txt==--
Inner content
--==ATTACHMENT_BLOCK_END==--
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    with pytest.raises(ProcessingError, match="Nested attachment blocks"):
        split_processor.process(content, output_files)

def test_malformed_content_invalid_markers(split_processor, tmp_path):
    """Test processing content with invalid attachment markers."""
    content = """
# Test Document

--==ATTACHMENT_BLOCK==--
Missing filename
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    with pytest.raises(ProcessingError, match="Invalid attachment block marker"):
        split_processor.process(content, output_files)

def test_missing_output_files(split_processor, tmp_path):
    """Test processing with missing output files configuration."""
    content = "# Test Document"
    
    with pytest.raises(ProcessingError, match="Missing required output files"):
        split_processor.process(content, {})

def test_invalid_output_paths(split_processor, tmp_path):
    """Test processing with invalid output paths."""
    content = "# Test Document"
    
    output_files = {
        'summary': tmp_path / 'invalid' / 'summary.md',
        'raw_notes': tmp_path / 'invalid' / 'raw_notes.md',
        'attachments': tmp_path / 'invalid' / 'attachments.md'
    }
    
    with pytest.raises(ProcessingError, match="Invalid output path"):
        split_processor.process(content, output_files)

def test_malformed_metadata(split_processor, tmp_path):
    """Test processing content with malformed metadata."""
    content = """
---
invalid: yaml: content
---

# Test Document
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    with pytest.raises(ProcessingError, match="Invalid metadata"):
        split_processor.process(content, output_files)

def test_malformed_navigation(split_processor, tmp_path):
    """Test processing content with malformed navigation comments."""
    content = """
# Test Document

<!-- prev: -->
<!-- next: missing -->
<!-- invalid navigation -->

Content
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should process but log warnings
    with pytest.warns(UserWarning, match="Invalid navigation comment"):
        split_processor.process(content, output_files)

def test_duplicate_attachment_names(split_processor, tmp_path):
    """Test processing content with duplicate attachment names."""
    content = """
# Test Document

--==ATTACHMENT_BLOCK: test.txt==--
First content
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: test.txt==--
Second content
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    with pytest.raises(ProcessingError, match="Duplicate attachment name"):
        split_processor.process(content, output_files)

def test_empty_attachment_block(split_processor, tmp_path):
    """Test processing content with empty attachment block."""
    content = """
# Test Document

--==ATTACHMENT_BLOCK: empty.txt==--
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    with pytest.warns(UserWarning, match="Empty attachment block"):
        metrics = split_processor.process(content, output_files)
        assert metrics['num_attachments'] == 1

def test_invalid_file_permissions(split_processor, tmp_path):
    """Test processing with invalid file permissions."""
    content = "# Test Document"
    
    # Create output files with read-only permissions
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    for path in output_files.values():
        path.touch()
        path.chmod(0o444)  # Read-only
    
    with pytest.raises(ProcessingError, match="Permission denied"):
        split_processor.process(content, output_files)

def test_edge_case_large_attachment(split_processor, tmp_path):
    """Test processing content with very large attachment."""
    # Create large attachment content
    large_content = "Large content " * 1000000  # ~12MB of text
    
    content = f"""
# Test Document

--==ATTACHMENT_BLOCK: large.txt==--
{large_content}
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should process but might take longer
    metrics = split_processor.process(content, output_files)
    assert metrics['total_size'] > len(large_content)
    assert metrics['processing_time'] > 0

def test_edge_case_many_attachments(split_processor, tmp_path):
    """Test processing content with many small attachments."""
    # Create content with many attachments
    content_parts = []
    for i in range(10000):  # 10,000 attachments
        content_parts.extend([
            f"--==ATTACHMENT_BLOCK: file{i}.txt==--",
            f"Content {i}",
            "--==ATTACHMENT_BLOCK_END==--"
        ])
    
    content = "\n".join(content_parts)
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    # Should process but might take longer
    metrics = split_processor.process(content, output_files)
    assert metrics['num_attachments'] == 10000

def test_edge_case_unicode(split_processor, tmp_path):
    """Test processing content with various Unicode characters."""
    content = """
# Test Document 🚀

--==ATTACHMENT_BLOCK: unicode.txt==--
Unicode content: 你好世界
Emojis: 🌟 🎉 🎨
Special chars: ™ © ® ¥ € 
Math symbols: ∑ ∏ ∆ ∞ ∫
--==ATTACHMENT_BLOCK_END==--
"""
    
    output_files = {
        'summary': tmp_path / 'summary.md',
        'raw_notes': tmp_path / 'raw_notes.md',
        'attachments': tmp_path / 'attachments.md'
    }
    
    metrics = split_processor.process(content, output_files)
    
    # Check that Unicode is preserved
    attachments_content = output_files['attachments'].read_text()
    assert "你好世界" in attachments_content
    assert "🌟 🎉 🎨" in attachments_content 