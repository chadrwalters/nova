"""Tests for markdown aggregation processor."""

import os
from pathlib import Path
import pytest

from nova.processors.markdown_aggregate import MarkdownAggregateProcessor
from nova.core.errors import ProcessingError
from nova.core.config import NovaConfig, ProcessorConfig, PathsConfig

@pytest.fixture
def processor_config():
    """Create test processor config."""
    return ProcessorConfig(options={
        'components': {
            'aggregate_processor': {
                'config': {
                    'output_filename': 'all_merged_markdown.md',
                    'include_file_headers': True,
                    'add_separators': True
                }
            },
            'consolidate_processor': {
                'config': {
                    'attachment_markers': {
                        'start': "--==ATTACHMENT_BLOCK: {filename}==--",
                        'end': "--==ATTACHMENT_BLOCK_END==--"
                    }
                }
            }
        }
    })

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
def processor(processor_config, nova_config):
    """Create test processor instance."""
    return MarkdownAggregateProcessor(processor_config, nova_config)

@pytest.fixture
def test_files(tmp_path):
    """Create test files and directories."""
    # Create input directory
    input_dir = tmp_path / "input"
    input_dir.mkdir()
    
    # Create test files with different content types
    structured_file = input_dir / "structured.md"
    structured_file.write_text("""# Structured Document
* Point 1
* Point 2
* Point 3

--==ATTACHMENT_BLOCK: struct.pdf==--
Structured attachment content
--==ATTACHMENT_BLOCK_END==--""")
    
    chronological_file = input_dir / "20240320_notes.md"
    chronological_file.write_text("""# Meeting Notes 2024-03-20
Notes content here

--==ATTACHMENT_BLOCK: notes.md==--
Meeting notes attachment
--==ATTACHMENT_BLOCK_END==--""")
    
    mixed_file = input_dir / "mixed.md"
    mixed_file.write_text("""# Mixed Content
Some regular content

--==RAW NOTES==--
Raw notes content

--==ATTACHMENT_BLOCK: mixed.jpg==--
Mixed attachment content
--==ATTACHMENT_BLOCK_END==--""")
    
    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    return {
        'input_dir': input_dir,
        'output_dir': output_dir,
        'structured_file': structured_file,
        'chronological_file': chronological_file,
        'mixed_file': mixed_file
    }

def test_extract_attachment_blocks(processor):
    """Test extraction of attachment blocks."""
    content = """# Document
Some content

--==ATTACHMENT_BLOCK: file1.md==--
Attachment 1 content
--==ATTACHMENT_BLOCK_END==--

More content

--==ATTACHMENT_BLOCK: file2.md==--
Attachment 2 content
--==ATTACHMENT_BLOCK_END==--"""

    cleaned_content, blocks = processor._extract_attachment_blocks(content)
    
    # Verify blocks are extracted
    assert len(blocks) == 2
    assert blocks[0].filename == 'file1.md'
    assert blocks[0].content == 'Attachment 1 content'
    assert blocks[1].filename == 'file2.md'
    assert blocks[1].content == 'Attachment 2 content'
    
    # Verify content is cleaned
    assert 'Attachment 1 content' not in cleaned_content
    assert 'Attachment 2 content' not in cleaned_content

def test_add_file_header(processor):
    """Test adding file headers to content."""
    content = "# Test Content"
    file_path = Path("test.md")
    
    # Test with headers enabled
    processor.include_file_headers = True
    with_header = processor._add_file_header(content, file_path)
    assert "## File: test.md" in with_header
    assert "# Test Content" in with_header
    
    # Test with headers disabled
    processor.include_file_headers = False
    without_header = processor._add_file_header(content, file_path)
    assert "## File:" not in without_header
    assert content == without_header

def test_analyze_content(processor):
    """Test content analysis."""
    # Test structured content
    structured = """# Document
* Point 1
* Point 2
- Point 3
1. Point 4"""
    struct_analysis = processor._analyze_content(structured)
    assert struct_analysis['is_structured'] is True
    
    # Test chronological content
    chronological = """# Notes
2024-03-20: Meeting notes
Some notes here

2024-03-21: Follow-up
More notes"""
    chrono_analysis = processor._analyze_content(chronological)
    assert chrono_analysis['is_chronological'] is True
    
    # Test content with metadata
    with_metadata = """# Document
<!-- {"author": "Test"} -->
Content"""
    meta_analysis = processor._analyze_content(with_metadata)
    assert meta_analysis['has_metadata'] is True
    
    # Test content with attachments
    with_attachments = """# Document
--==ATTACHMENT_BLOCK: file.md==--
Content
--==ATTACHMENT_BLOCK_END==--"""
    attach_analysis = processor._analyze_content(with_attachments)
    assert attach_analysis['has_attachments'] is True

def test_process_with_mixed_content(processor, test_files):
    """Test processing files with mixed content types."""
    input_files = [
        test_files['structured_file'],
        test_files['chronological_file'],
        test_files['mixed_file']
    ]
    
    output_file = test_files['output_dir'] / "all_merged_markdown.md"
    processor.process(input_files, test_files['output_dir'])
    
    # Verify output file exists
    assert output_file.exists()
    content = output_file.read_text()
    
    # Verify content is present
    assert "# Aggregated Markdown" in content
    assert "* Point 1" in content
    assert "2024-03-20" in content
    assert "Mixed Content" in content
    
    # Verify attachments are preserved
    assert "--==ATTACHMENT_BLOCK: struct.pdf==--" in content
    assert "--==ATTACHMENT_BLOCK: notes.md==--" in content
    assert "--==ATTACHMENT_BLOCK: mixed.jpg==--" in content
    assert "Structured attachment content" in content
    assert "Meeting notes attachment" in content
    assert "Mixed attachment content" in content
    
    # Verify separators are present
    assert "\n\n---\n\n" in content

def test_process_with_invalid_config(processor_config):
    """Test processor initialization with invalid config."""
    # Remove required config sections
    invalid_config = processor_config.model_dump()
    del invalid_config['options']['components']['aggregate_processor']['config']
    
    with pytest.raises(ProcessingError):
        config = ProcessorConfig(options=invalid_config['options'])
        nova_config = NovaConfig(paths=PathsConfig(
            base_dir=Path("/tmp/nova"),
            input_dir=Path("/tmp/nova/input"),
            output_dir=Path("/tmp/nova/output"),
            processing_dir=Path("/tmp/nova/processing"),
            temp_dir=Path("/tmp/nova/temp"),
            state_dir=Path("/tmp/nova/state"),
            phase_dirs={
                "markdown_parse": Path("/tmp/nova/processing/markdown_parse"),
                "markdown_consolidate": Path("/tmp/nova/processing/markdown_consolidate"),
                "markdown_aggregate": Path("/tmp/nova/processing/markdown_aggregate"),
                "markdown_split": Path("/tmp/nova/processing/markdown_split")
            },
            image_dirs={
                "original": Path("/tmp/nova/processing/images/original"),
                "processed": Path("/tmp/nova/processing/images/processed"),
                "metadata": Path("/tmp/nova/processing/images/metadata"),
                "cache": Path("/tmp/nova/processing/images/cache")
            },
            office_dirs={
                "assets": Path("/tmp/nova/processing/office/assets"),
                "temp": Path("/tmp/nova/processing/office/temp")
            }
        ))
        MarkdownAggregateProcessor(config, nova_config)

def test_process_with_size_validation(processor, test_files):
    """Test content size validation during processing."""
    # Create a file with large content
    large_file = test_files['input_dir'] / "large.md"
    large_content = "# " + "Large content\n" * 1000
    large_file.write_text(large_content)
    
    output_file = test_files['output_dir'] / "all_merged_markdown.md"
    processor.process([large_file], test_files['output_dir'])
    
    # Verify output file exists and contains content
    assert output_file.exists()
    content = output_file.read_text()
    
    # Verify header and content
    assert "# Aggregated Markdown" in content
    assert "Large content" in content
    
    # Verify size is reasonable (header + content + separators)
    input_size = len(large_content.encode('utf-8'))
    output_size = len(content.encode('utf-8'))
    assert output_size > input_size  # Should be larger due to header and separators
    assert output_size < input_size * 1.2  # But not too much larger