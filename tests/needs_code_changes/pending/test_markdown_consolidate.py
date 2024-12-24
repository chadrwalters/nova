"""Tests for markdown consolidation processor."""

import os
from pathlib import Path
import pytest

from nova.processors.markdown_consolidate import MarkdownConsolidateProcessor
from nova.core.errors import ProcessingError
from nova.core.config import NovaConfig, ProcessorConfig, PathsConfig

@pytest.fixture
def processor_config():
    """Create test processor config."""
    return ProcessorConfig(options={
        'components': {
            'consolidate_processor': {
                'config': {
                    'group_by_root': True,
                    'handle_attachments': True,
                    'preserve_structure': True,
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
    return MarkdownConsolidateProcessor(processor_config, nova_config)

@pytest.fixture
def test_files(tmp_path):
    """Create test files and directories."""
    # Create main markdown file
    main_md = tmp_path / "test.md"
    main_md.write_text("# Main Document\n\nThis is the main content")
    
    # Create attachments directory
    attachments_dir = tmp_path / "test"
    attachments_dir.mkdir()
    
    # Create attachment files
    attachment1 = attachments_dir / "attachment1.md"
    attachment1.write_text("This is attachment 1 content")
    
    subdir = attachments_dir / "subdir"
    subdir.mkdir()
    attachment2 = subdir / "attachment2.md"
    attachment2.write_text("This is attachment 2 content")
    
    # Create output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    return {
        'main_md': main_md,
        'attachments_dir': attachments_dir,
        'output_dir': output_dir
    }

def test_find_attachments_dir(processor, test_files):
    """Test finding attachments directory."""
    attachments_dir = processor._find_attachments_dir(test_files['main_md'])
    assert attachments_dir == test_files['attachments_dir']
    
def test_merge_attachments(processor, test_files):
    """Test merging attachments into main content."""
    content = "# Original Content"
    merged = processor._merge_attachments(content, test_files['attachments_dir'])
    
    assert "--==ATTACHMENT_BLOCK: attachment1.md==--" in merged
    assert "This is attachment 1 content" in merged
    assert "--==ATTACHMENT_BLOCK_END==--" in merged
    
    assert "--==ATTACHMENT_BLOCK: subdir/attachment2.md==--" in merged
    assert "This is attachment 2 content" in merged
    assert "--==ATTACHMENT_BLOCK_END==--" in merged
    
def test_process_with_attachments(processor, test_files):
    """Test processing a markdown file with attachments."""
    output_path = test_files['output_dir'] / "test.md"
    result = processor.process(test_files['main_md'], output_path)
    
    assert result == output_path
    assert output_path.exists()
    
    content = output_path.read_text()
    assert "# Main Document" in content
    assert "This is the main content" in content
    assert "--==ATTACHMENT_BLOCK: attachment1.md==--" in content
    assert "This is attachment 1 content" in content
    assert "--==ATTACHMENT_BLOCK: subdir/attachment2.md==--" in content
    assert "This is attachment 2 content" in content

def test_process_without_attachments(processor, test_files):
    """Test processing a markdown file without attachments."""
    # Create a markdown file without attachments
    no_attachments_md = test_files['main_md'].parent / "no_attachments.md"
    no_attachments_md.write_text("# No Attachments\n\nThis file has no attachments.")
    
    output_path = test_files['output_dir'] / "no_attachments.md"
    result = processor.process(no_attachments_md, output_path)
    
    assert result == output_path
    assert output_path.exists()
    
    content = output_path.read_text()
    assert "# No Attachments" in content
    assert "This file has no attachments" in content
    assert "--==ATTACHMENT_BLOCK:" not in content
    
def test_process_error_handling(processor):
    """Test error handling during processing."""
    with pytest.raises(ProcessingError):
        processor.process(
            Path("nonexistent.md"),
            Path("output.md")
        )

def test_validate_markers(processor):
    """Test attachment marker validation."""
    # Valid markers
    content = """
    Some content
    --==ATTACHMENT_BLOCK: file1.md==--
    Content 1
    --==ATTACHMENT_BLOCK_END==--
    More content
    --==ATTACHMENT_BLOCK: file2.md==--
    Content 2
    --==ATTACHMENT_BLOCK_END==--
    """
    assert processor._validate_markers(content) is True
    
    # Mismatched count
    content = """
    Some content
    --==ATTACHMENT_BLOCK: file1.md==--
    Content 1
    --==ATTACHMENT_BLOCK_END==--
    --==ATTACHMENT_BLOCK: file2.md==--
    Content 2
    """
    assert processor._validate_markers(content) is False
    
    # Invalid ordering
    content = """
    Some content
    --==ATTACHMENT_BLOCK_END==--
    Content 1
    --==ATTACHMENT_BLOCK: file1.md==--
    """
    assert processor._validate_markers(content) is False

def test_has_attachment_markers(processor):
    """Test detection of existing attachment markers."""
    # Content with markers
    content = """Some content
    --==ATTACHMENT_BLOCK: file.md==--
    Content
    --==ATTACHMENT_BLOCK_END==--
    """
    assert processor._has_attachment_markers(content) is True
    
    # Content without markers
    content = "Some content\nwithout markers"
    assert processor._has_attachment_markers(content) is False

def test_normalize_references(processor):
    """Test normalization of attachment references."""
    # Test old-style markers
    content = """# Document
[Begin Attachment]: file1.md
Content 1
<attached file2.md>
Content 2
[attachment: file3.md]
Content 3
"""
    normalized = processor._normalize_references(content)
    
    assert "--==ATTACHMENT_BLOCK: file1.md==--" in normalized
    assert "--==ATTACHMENT_BLOCK: file2.md==--" in normalized
    assert "--==ATTACHMENT_BLOCK: file3.md==--" in normalized
    assert "[Begin Attachment]:" not in normalized
    assert "<attached" not in normalized
    assert "[attachment:" not in normalized

def test_extract_metadata(processor):
    """Test metadata extraction from content."""
    content = """# Document
<!-- {"author": "Test User", "date": "2024-03-20"} -->
Some content
<!-- {"tags": ["test", "markdown"]} -->
More content
"""
    metadata = processor._extract_metadata(content)
    
    assert metadata["author"] == "Test User"
    assert metadata["date"] == "2024-03-20"
    assert "test" in metadata["tags"]
    assert "markdown" in metadata["tags"]

def test_process_with_existing_markers(processor, test_files):
    """Test processing a file that already has attachment markers."""
    # Create a file with existing markers
    marked_attachment = test_files['attachments_dir'] / "marked.md"
    marked_attachment.write_text("""--==ATTACHMENT_BLOCK: existing.md==--
This content is already marked
--==ATTACHMENT_BLOCK_END==--""")
    
    output_path = test_files['output_dir'] / "test.md"
    result = processor.process(test_files['main_md'], output_path)
    
    content = output_path.read_text()
    # Verify the existing markers are preserved
    assert "--==ATTACHMENT_BLOCK: existing.md==--" in content
    assert "This content is already marked" in content
    # Verify other attachments are still processed
    assert "--==ATTACHMENT_BLOCK: attachment1.md==--" in content
    assert "This is attachment 1 content" in content

def test_process_with_mixed_references(processor, test_files):
    """Test processing a file with mixed reference styles."""
    # Create a file with mixed reference styles
    main_content = """# Main Document
[Begin Attachment]: old_style.md
Old style content
<attached html_style.md>
HTML style content
[attachment: bracket_style.md]
Bracket style content
"""
    test_files['main_md'].write_text(main_content)
    
    output_path = test_files['output_dir'] / "test.md"
    result = processor.process(test_files['main_md'], output_path)
    
    content = output_path.read_text()
    # Verify all references are normalized
    assert "--==ATTACHMENT_BLOCK: old_style.md==--" in content
    assert "--==ATTACHMENT_BLOCK: html_style.md==--" in content
    assert "--==ATTACHMENT_BLOCK: bracket_style.md==--" in content
    # Verify old formats are removed
    assert "[Begin Attachment]:" not in content
    assert "<attached" not in content
    assert "[attachment:" not in content

def test_process_with_metadata(processor, test_files):
    """Test processing a file with metadata."""
    # Create a file with metadata
    main_content = """# Main Document
<!-- {"title": "Test Document", "author": "Test User"} -->
Some content
<!-- {"category": "test", "tags": ["markdown", "test"]} -->
More content
"""
    test_files['main_md'].write_text(main_content)
    
    output_path = test_files['output_dir'] / "test.md"
    result = processor.process(test_files['main_md'], output_path)
    
    content = output_path.read_text()
    # Verify metadata is preserved
    assert '{"title": "Test Document"' in content
    assert '{"category": "test"' in content
    # Verify content is preserved
    assert "Some content" in content
    assert "More content" in content