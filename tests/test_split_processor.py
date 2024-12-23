"""Tests for ThreeFileSplitProcessor."""

import pytest
from pathlib import Path
from nova.core.config import ProcessorConfig, NovaConfig, PathsConfig, ThreeFileSplitConfig

from nova.processors.three_file_split_processor import ThreeFileSplitProcessor
from nova.core.errors import ProcessingError

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
    """Create a nova config for testing."""
    paths_config = PathsConfig(
        base_dir=tmp_path,
        input_dir=tmp_path / 'input',
        output_dir=tmp_path / 'output',
        processing_dir=tmp_path / 'processing',
        temp_dir=tmp_path / 'temp',
        state_dir=tmp_path / 'state',
        phase_dirs={
            'markdown_parse': tmp_path / 'phases/markdown_parse',
            'markdown_consolidate': tmp_path / 'phases/markdown_consolidate',
            'markdown_aggregate': tmp_path / 'phases/markdown_aggregate',
            'markdown_split': tmp_path / 'phases/markdown_split'
        },
        image_dirs={
            'original': tmp_path / 'images/original',
            'processed': tmp_path / 'images/processed',
            'metadata': tmp_path / 'images/metadata',
            'cache': tmp_path / 'images/cache'
        },
        office_dirs={
            'assets': tmp_path / 'office/assets',
            'temp': tmp_path / 'office/temp'
        }
    )
    return NovaConfig(paths=paths_config)

@pytest.fixture
def split_processor(processor_config, nova_config):
    """Create a ThreeFileSplitProcessor instance for testing."""
    return ThreeFileSplitProcessor(processor_config, nova_config)

@pytest.fixture
def setup_files(tmp_path):
    """Set up test files."""
    input_dir = tmp_path / 'input'
    input_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / 'output'
    output_dir.mkdir(exist_ok=True)

    # Create test files
    test_file = input_dir / 'test.md'
    test_file.write_text("""
--==SUMMARY==--
# Test Document
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

def test_split_content_basic(split_processor, setup_files, tmp_path):
    """Test basic content splitting."""
    input_dir, output_dir = setup_files(tmp_path)

    # Process content
    split_processor.process(input_dir / 'test.md', output_dir)
    
    # Check summary file
    summary_file = output_dir / 'summary.md'
    assert summary_file.exists()
    summary_content = summary_file.read_text()
    assert "Test Document" in summary_content
    assert "This is a summary section" in summary_content
    assert "--==ATTACHMENT_BLOCK:" not in summary_content
    
    # Check raw notes file
    raw_notes_file = output_dir / 'raw_notes.md'
    assert raw_notes_file.exists()
    raw_notes_content = raw_notes_file.read_text()
    assert "Raw Notes" in raw_notes_content
    assert "These are some raw notes" in raw_notes_content
    assert "--==ATTACHMENT_BLOCK:" not in raw_notes_content
    
    # Check attachments file
    attachments_file = output_dir / 'attachments.md'
    assert attachments_file.exists()
    attachments_content = attachments_file.read_text()
    assert "--==ATTACHMENT_BLOCK: test.txt==--" in attachments_content
    assert "--==ATTACHMENT_BLOCK: data.csv==--" in attachments_content
    assert "This is a test file content" in attachments_content
    assert "col1,col2" in attachments_content

def test_split_content_with_references(split_processor, setup_files, tmp_path):
    """Test content splitting with cross-references."""
    input_dir, output_dir = setup_files(tmp_path)

    content = """
# Test Document

See [[Reference 1]] for details.

--==ATTACHMENT_BLOCK: test.txt==--
This references [[Reference 2]]
--==ATTACHMENT_BLOCK_END==--

Also see [[Reference 1]] again.
"""
    
    split_processor.process(input_dir / 'test.md', output_dir)
    
    # Check reference preservation
    summary_content = output_dir / 'summary.md'
    raw_notes_content = output_dir / 'raw_notes.md'
    attachments_content = output_dir / 'attachments.md'
    
    assert "[[Reference 1]]" in summary_content or raw_notes_content
    assert "[[Reference 2]]" in attachments_content

def test_split_content_with_navigation(split_processor, setup_files, tmp_path):
    """Test content splitting with navigation links."""
    input_dir, output_dir = setup_files(tmp_path)

    content = """
# Test Document

<!-- prev: prev.md -->
<!-- next: next.md -->

Some content.

--==ATTACHMENT_BLOCK: test.txt==--
Attachment content
--==ATTACHMENT_BLOCK_END==--

More content.
"""
    
    split_processor.process(input_dir / 'test.md', output_dir)
    
    # Check navigation preservation
    summary_content = output_dir / 'summary.md'
    assert "<!-- prev: prev.md -->" in summary_content
    assert "<!-- next: next.md -->" in summary_content

def test_split_content_empty_sections(split_processor, setup_files, tmp_path):
    """Test content splitting with empty sections."""
    input_dir, output_dir = setup_files(tmp_path)

    content = """
--==ATTACHMENT_BLOCK: test.txt==--
Only attachment content
--==ATTACHMENT_BLOCK_END==--
"""
    
    split_processor.process(input_dir / 'test.md', output_dir)
    
    # Check empty files are still created
    summary_file = output_dir / 'summary.md'
    assert summary_file.exists()
    raw_notes_file = output_dir / 'raw_notes.md'
    assert raw_notes_file.exists()
    attachments_file = output_dir / 'attachments.md'
    assert attachments_file.exists()
    
    # Check only attachments has content
    assert summary_file.read_text().strip() == ""
    assert raw_notes_file.read_text().strip() == ""
    assert len(attachments_file.read_text().strip()) > 0

def test_split_content_distribution_metrics(split_processor, setup_files, tmp_path):
    """Test content distribution metrics."""
    input_dir, output_dir = setup_files(tmp_path)

    metrics = split_processor.process(input_dir / 'test.md', output_dir)
    
    # Check metrics
    assert 'total_size' in metrics
    assert 'distribution' in metrics
    assert set(metrics['distribution'].keys()) == {'summary', 'raw_notes', 'attachments'}
    assert sum(metrics['distribution'].values()) == 100  # Percentages should sum to 100

def test_split_content_invalid_markers(split_processor, setup_files, tmp_path):
    """Test content splitting with invalid attachment markers."""
    input_dir, output_dir = setup_files(tmp_path)

    content = """
Some content

--==ATTACHMENT_BLOCK: test.txt==--
Unclosed attachment block

--==ATTACHMENT_BLOCK: another.txt==--
Nested attachment?
--==ATTACHMENT_BLOCK_END==--

More content
"""
    
    with pytest.raises(ProcessingError, match="Unclosed attachment block"):
        split_processor.process(input_dir / 'test.md', output_dir)

def test_split_content_with_relative_paths(split_processor, setup_files, tmp_path):
    """Test content splitting with relative paths."""
    input_dir, output_dir = setup_files(tmp_path)

    content = """
# Test Document

![Image](images/test.jpg)

--==ATTACHMENT_BLOCK: doc.pdf==--
See file at ../data/file.txt
--==ATTACHMENT_BLOCK_END==--

More content with ./local/path.
"""
    
    split_processor.process(input_dir / 'test.md', output_dir)
    
    # Check path handling
    summary_content = output_dir / 'summary.md'
    attachments_content = output_dir / 'attachments.md'
    
    assert "images/test.jpg" in summary_content  # Paths in content preserved
    assert "../data/file.txt" in attachments_content  # Paths in attachments preserved

def test_split_content_large_file(split_processor, setup_files, tmp_path):
    """Test content splitting with a large file."""
    input_dir, output_dir = setup_files(tmp_path)

    # Create large content with multiple attachments
    content_parts = []
    for i in range(100):
        content_parts.extend([
            f"# Section {i}",
            "Some content " * 100,
            f"--==ATTACHMENT_BLOCK: file{i}.txt==--",
            "Attachment content " * 100,
            "--==ATTACHMENT_BLOCK_END==--",
            "More content " * 100
        ])
    
    content = "\n\n".join(content_parts)
    
    split_processor.process(content, output_dir)
    
    # Check all files exist and have content
    summary_file = output_dir / 'summary.md'
    raw_notes_file = output_dir / 'raw_notes.md'
    attachments_file = output_dir / 'attachments.md'
    assert all(f.exists() and f.stat().st_size > 0 for f in [summary_file, raw_notes_file, attachments_file])
    
    # Check performance metrics
    assert 'processing_time' in metrics
    assert 'memory_usage' in metrics

def test_split_content_with_metadata(split_processor, setup_files, tmp_path):
    """Test content splitting with metadata preservation."""
    input_dir, output_dir = setup_files(tmp_path)

    content = """
---
title: Test Document
author: Test Author
date: 2024-01-01
---

# Content

--==ATTACHMENT_BLOCK: test.txt==--
Attachment content
--==ATTACHMENT_BLOCK_END==--
"""
    
    split_processor.process(input_dir / 'test.md', output_dir)
    
    # Check metadata preservation
    summary_content = output_dir / 'summary.md'
    assert "title: Test Document" in summary_content
    assert "author: Test Author" in summary_content
    assert "date: 2024-01-01" in summary_content 