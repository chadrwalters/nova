"""Tests for ThreeFileSplitProcessor."""

import pytest
from pathlib import Path
from nova.core.models import LoggingConfig, PathsConfig
from nova.core.config import (
    NovaConfig, ProcessorConfig, MarkdownConfig, ImageConfig, OfficeConfig,
    OpenAIConfig, RetryConfig, CacheConfig, EmbedConfig
)
from nova.core.errors import ProcessingError
from nova.core.logging import get_logger

logger = get_logger(__name__)

@pytest.fixture
def processor_config():
    """Create a test processor configuration."""
    return ProcessorConfig(
        output_files={
            'summary': 'summary.md',
            'raw_notes': 'raw_notes.md',
            'attachments': 'attachments.md'
        },
        section_markers={
            'summary': '--==SUMMARY==--',
            'raw_notes': '--==RAW_NOTES==--',
            'attachments': '--==ATTACHMENTS==--'
        },
        attachment_markers={
            'start': '--==ATTACHMENT_BLOCK: {filename}==--',
            'end': '--==ATTACHMENT_BLOCK_END==--'
        },
        content_type_rules={
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
        content_preservation={
            'validate_input_size': True,
            'validate_output_size': True,
            'track_content_markers': True,
            'verify_section_integrity': True
        },
        cross_linking=True,
        preserve_headers=True
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
    """Create a ThreeFileSplitProcessor instance for testing."""
    return ThreeFileSplitProcessor(processor_config, nova_config)

@pytest.fixture
def setup_files(tmp_path):
    """Create test files and directories."""
    input_dir = tmp_path / 'input'
    output_dir = tmp_path / 'output'
    
    # Create directories
    input_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create test file
    test_file = input_dir / 'test.md'
    test_file.write_text("""# Test Document

--==SUMMARY==--
This is a summary section.
[Link to attachment](test.txt)

--==RAW_NOTES==--
## Raw Notes
These are some raw notes.
See [another attachment](data.csv)

--==ATTACHMENTS==--
--==ATTACHMENT_BLOCK: test.txt==--
This is a test file content.
--==ATTACHMENT_BLOCK_END==--

--==ATTACHMENT_BLOCK: data.csv==--
col1,col2
1,2
3,4
--==ATTACHMENT_BLOCK_END==--
""")
    
    return input_dir, output_dir

@pytest.fixture
def output_files(tmp_path):
    """Create output file paths."""
    output_dir = tmp_path / 'output'
    output_dir.mkdir(parents=True, exist_ok=True)
    
    return {
        'summary': output_dir / 'summary.md',
        'raw_notes': output_dir / 'raw_notes.md',
        'attachments': output_dir / 'attachments.md'
    }

def test_split_content_basic(split_processor, setup_files, output_files):
    """Test basic content splitting."""
    input_dir, _ = setup_files
    test_file = input_dir / 'test.md'

    # Create test file
    test_file.write_text("""# Test Document

--==SUMMARY==--
This is a summary section.

--==RAW_NOTES==--
These are raw notes.

--==ATTACHMENTS==--
[Link to attachment](test.txt)
""")

    # Process should succeed
    output_paths = split_processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Verify content of each file
    summary_content = output_files['summary'].read_text()
    assert "# Test Document" in summary_content
    assert "This is a summary section." in summary_content

    raw_notes = output_files['raw_notes'].read_text()
    assert "These are raw notes." in raw_notes

    attachments = output_files['attachments'].read_text()
    assert "[Link to attachment](test.txt)" in attachments

def test_split_content_with_references(split_processor, setup_files, output_files):
    """Test content splitting with cross-references."""
    input_dir, _ = setup_files

    # Create test file with references
    test_file = input_dir / 'test.md'
    test_file.write_text("""# Test Document

--==SUMMARY==--
This is a summary section.
See [[Reference 1]] for details.

--==RAW_NOTES==--
These are raw notes.
Related to [[Reference 2]].

--==ATTACHMENTS==--
[[Reference 1]]: First reference content
[[Reference 2]]: Second reference content
""")

    # Process the file
    output_paths = split_processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Verify references are preserved
    summary_content = output_files['summary'].read_text()
    assert '[[Reference 1]]' in summary_content
    assert 'See [[Reference 1]] for details' in summary_content

    raw_notes_content = output_files['raw_notes'].read_text()
    assert '[[Reference 2]]' in raw_notes_content
    assert 'Related to [[Reference 2]]' in raw_notes_content

    attachments_content = output_files['attachments'].read_text()
    assert '[[Reference 1]]: First reference content' in attachments_content
    assert '[[Reference 2]]: Second reference content' in attachments_content

def test_split_content_with_navigation(split_processor, setup_files, output_files):
    """Test content splitting with navigation links."""
    input_dir, _ = setup_files

    # Create test file with navigation
    test_file = input_dir / 'test.md'
    test_file.write_text("""# Test Document

--==SUMMARY==--
This is a summary section.
← [Previous](prev.md)
→ [Next](next.md)

--==RAW_NOTES==--
These are raw notes.

--==ATTACHMENTS==--
Navigation links should be preserved.
""")

    # Process the file
    output_paths = split_processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Verify navigation links are preserved
    summary_content = output_files['summary'].read_text()
    assert '[Previous](prev.md)' in summary_content
    assert '[Next](next.md)' in summary_content

def test_split_content_empty_sections(split_processor, setup_files, output_files):
    """Test content splitting with empty sections."""
    input_dir, _ = setup_files

    # Create test file with empty sections
    test_file = input_dir / 'test.md'
    test_file.write_text("""# Test Document

--==SUMMARY==--

--==RAW_NOTES==--

--==ATTACHMENTS==--
""")

    # Process should fail due to empty sections
    with pytest.raises(ProcessingError, match="No content found in any section"):
        split_processor.process(test_file, output_files)

def test_split_content_distribution_metrics(split_processor, setup_files, output_files):
    """Test content distribution metrics."""
    input_dir, _ = setup_files

    # Create test file with varying content sizes
    test_file = input_dir / 'test.md'
    test_file.write_text("""# Test Document

--==SUMMARY==--
Short summary.

--==RAW_NOTES==--
Longer raw notes section with
multiple lines of content
and more details.

--==ATTACHMENTS==--
Medium sized attachment section
with some content.
""")

    # Process the file
    output_paths = split_processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Verify content distribution
    summary_size = len(output_files['summary'].read_text())
    raw_notes_size = len(output_files['raw_notes'].read_text())
    attachments_size = len(output_files['attachments'].read_text())

    assert summary_size < raw_notes_size  # Raw notes should be longer
    assert attachments_size > summary_size  # Attachments should be longer than summary

def test_split_content_invalid_markers(split_processor, setup_files, output_files):
    """Test content splitting with invalid markers."""
    input_dir, _ = setup_files

    # Create test file with invalid markers
    test_file = input_dir / 'test.md'
    test_file.write_text("""# Test Document

--==INVALID==--
This is an invalid section.

--==RAW_NOTES==--
These are raw notes.

--==ATTACHMENTS==--
Valid attachment section.
""")

    # Process should fail due to invalid section marker
    with pytest.raises(ProcessingError) as exc_info:
        split_processor.process(test_file, output_files)
    assert "Invalid section marker: INVALID" in str(exc_info.value)

def test_split_content_with_relative_paths(split_processor, setup_files, output_files):
    """Test content splitting with relative paths."""
    input_dir, _ = setup_files

    # Create test file with relative paths
    test_file = input_dir / 'test.md'
    test_file.write_text("""# Test Document

--==SUMMARY==--
This is a summary section.
[Link](./images/test.png)

--==RAW_NOTES==--
These are raw notes.
[Another link](../data/file.txt)

--==ATTACHMENTS==--
Attachment with relative paths.
""")

    # Process the file
    output_paths = split_processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Verify relative paths are preserved
    summary_content = output_files['summary'].read_text()
    assert '[Link](./images/test.png)' in summary_content

    raw_notes_content = output_files['raw_notes'].read_text()
    assert '[Another link](../data/file.txt)' in raw_notes_content

def test_split_content_large_file(split_processor, setup_files, output_files):
    """Test content splitting with a large file."""
    input_dir, _ = setup_files

    # Create large test file
    test_file = input_dir / 'test.md'
    large_content = []
    for i in range(100):  # Create 100 sections
        large_content.extend([
            f"# Section {i}",
            "--==SUMMARY==--",
            f"Summary for section {i}\n" * 5,
            "--==RAW_NOTES==--",
            f"Raw notes for section {i}\n" * 10,
            "--==ATTACHMENTS==--",
            f"Attachments for section {i}\n" * 3
        ])
    test_file.write_text("\n".join(large_content))

    # Process the file
    output_paths = split_processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Verify large file handling
    for output_file in output_files.values():
        assert output_file.exists()
        content = output_file.read_text()
        assert len(content) > 1000  # Each file should have significant content

def test_split_content_with_metadata(split_processor, setup_files, output_files):
    """Test content splitting with metadata preservation."""
    input_dir, _ = setup_files

    # Create test file with metadata
    test_file = input_dir / 'test.md'
    test_file.write_text("""---
title: Test Document
author: Test Author
date: 2024-01-01
---

--==SUMMARY==--
This is a summary section.

--==RAW_NOTES==--
These are raw notes.

--==ATTACHMENTS==--
This is an attachment section.
""")

    # Process the file
    output_paths = split_processor.process(test_file, output_files)
    assert len(output_paths) == 3

    # Verify metadata is preserved
    summary_content = output_files['summary'].read_text()
    assert 'title: Test Document' in summary_content
    assert 'author: Test Author' in summary_content
    assert 'date: 2024-01-01' in summary_content 