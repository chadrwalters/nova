"""Test cases for markdown aggregate processor."""

import pytest
from pathlib import Path
import os
from typing import Dict, Any

from nova.phases.aggregate.processor import MarkdownAggregateProcessor
from nova.core.config import ProcessorConfig, PipelineConfig, PathConfig

@pytest.fixture
def test_files(tmp_path):
    """Create test files and directories."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    
    return {
        "input_dir": input_dir,
        "output_dir": output_dir
    }

@pytest.fixture
def processor(test_files):
    """Create processor instance with test configuration."""
    config = ProcessorConfig(
        name="markdown_aggregate",
        description="Aggregate markdown files into a single file",
        processor="MarkdownAggregateProcessor",
        output_dir=str(test_files["output_dir"]),
        options={
            "output_filename": "all_merged_markdown.md",
            "include_file_headers": True,
            "add_separators": True
        }
    )
    pipeline_config = PipelineConfig(
        paths=PathConfig(
            base_dir=str(test_files["input_dir"].parent)
        ),
        phases=[config],
        input_dir=str(test_files["input_dir"]),
        output_dir=str(test_files["output_dir"]),
        processing_dir=str(test_files["input_dir"] / "processing"),
        temp_dir=str(test_files["input_dir"] / "temp")
    )
    
    # Set up environment variables for test
    os.environ["NOVA_PHASE_MARKDOWN_CONSOLIDATE"] = str(test_files["input_dir"])
    os.environ["NOVA_PHASE_MARKDOWN_AGGREGATE"] = str(test_files["output_dir"])
    
    return MarkdownAggregateProcessor(processor_config=config, pipeline_config=pipeline_config)

@pytest.fixture
def pipeline_config(tmp_path):
    """Create a basic pipeline configuration for testing."""
    return PipelineConfig(
        paths=PathConfig(
            base_dir=str(tmp_path)
        ),
        phases=[
            ProcessorConfig(
                name="MARKDOWN_AGGREGATE",
                description="Aggregate markdown files",
                output_dir=str(tmp_path / "output"),
                processor="MarkdownAggregateProcessor",
                input_dir=str(tmp_path / "input")
            )
        ],
        input_dir=str(tmp_path / "input"),
        output_dir=str(tmp_path / "output"),
        processing_dir=str(tmp_path / "processing"),
        temp_dir=str(tmp_path / "temp")
    )

# Hero Test Cases

async def test_basic_aggregation(processor, test_files):
    """Test basic aggregation of markdown files."""
    await processor.setup()
    success = await processor.process()
    assert success
    
    output_file = test_files["output_dir"] / "all_merged_markdown.md"
    assert output_file.exists()
    
    content = output_file.read_text()
    assert "--==SUMMARY==--" in content
    assert "--==RAW NOTES==--" in content
    assert "--==ATTACHMENTS==--" in content

async def test_section_markers(processor, test_files):
    """Test proper handling of section markers."""
    await processor.setup()
    success = await processor.process()
    assert success
    
    content = (test_files["output_dir"] / "all_merged_markdown.md").read_text()
    
    # Check section ordering
    summary_pos = content.find("--==SUMMARY==--")
    raw_notes_pos = content.find("--==RAW NOTES==--")
    attachments_pos = content.find("--==ATTACHMENTS==--")
    
    assert summary_pos < raw_notes_pos < attachments_pos

async def test_file_headers(processor, test_files):
    """Test inclusion of file headers."""
    await processor.setup()
    success = await processor.process()
    assert success
    
    content = (test_files["output_dir"] / "all_merged_markdown.md").read_text()
    assert "<!-- START_FILE: summary1.md -->" in content
    assert "<!-- END_FILE: summary1.md -->" in content

# Edge Cases

async def test_no_input_files(processor, test_files):
    """Test handling when no input files exist."""
    # Remove all input files
    for file in test_files["input_dir"].glob("*.md"):
        file.unlink()
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Should create output file even if empty
    output_file = test_files["output_dir"] / "all_merged_markdown.md"
    assert output_file.exists()
    assert output_file.stat().st_size > 0  # Should contain at least section markers

async def test_missing_section_markers(processor, test_files):
    """Test handling of files without section markers."""
    # Create file without section markers
    (test_files["input_dir"] / "no_markers.md").write_text("""# No Markers
Just regular content without any section markers
""")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    content = (test_files["output_dir"] / "all_merged_markdown.md").read_text()
    assert "No Markers" in content

async def test_duplicate_section_markers(processor, test_files):
    """Test handling of duplicate section markers."""
    # Create file with duplicate markers
    (test_files["input_dir"] / "duplicate_markers.md").write_text("""# Duplicate Markers
--==SUMMARY==--
First summary
--==SUMMARY==--
Second summary
""")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    content = (test_files["output_dir"] / "all_merged_markdown.md").read_text()
    assert "First summary" in content
    assert "Second summary" in content

async def test_nested_section_markers(processor, test_files):
    """Test handling of nested section markers."""
    nested_content = """# Nested Markers
--==SUMMARY==--
Summary content
--==RAW NOTES==--
Raw notes with --==SUMMARY==-- inside
--==ATTACHMENTS==--
"""
    (test_files["input_dir"] / "nested_markers.md").write_text(nested_content)
    
    await processor.setup()
    success = await processor.process()
    assert success

async def test_malformed_markers(processor, test_files):
    """Test handling of malformed section markers."""
    malformed_content = """# Malformed Markers
--==SUMARY==--  # Misspelled
--==RAW-NOTES==--  # Wrong format
--==ATTACHMENTS==  # Missing end
"""
    (test_files["input_dir"] / "malformed.md").write_text(malformed_content)
    
    await processor.setup()
    success = await processor.process()
    assert success

async def test_file_order_preservation(processor, test_files):
    """Test preservation of file processing order."""
    # Create numbered files
    for i in range(1, 4):
        (test_files["input_dir"] / f"{i}_test.md").write_text(f"# Test {i}")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    content = (test_files["output_dir"] / "all_merged_markdown.md").read_text()
    # Check order preservation
    pos1 = content.find("Test 1")
    pos2 = content.find("Test 2")
    pos3 = content.find("Test 3")
    assert pos1 < pos2 < pos3

async def test_mixed_content_types(processor, test_files):
    """Test handling of mixed content types in same file."""
    mixed_content = """# Mixed Content
--==SUMMARY==--
Summary part
--==RAW NOTES==--
Raw notes part
Regular content
--==ATTACHMENTS==--
[Attachment](file.pdf)
"""
    (test_files["input_dir"] / "mixed.md").write_text(mixed_content)
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    content = (test_files["output_dir"] / "all_merged_markdown.md").read_text()
    assert "Summary part" in content
    assert "Raw notes part" in content
    assert "Regular content" in content
    assert "[Attachment](file.pdf)" in content 

# Metadata-Driven Test Cases

async def test_metadata_extraction(processor, test_files):
    """Test extraction and preservation of metadata."""
    # Create test files with different content types
    (test_files["input_dir"] / "summary1.md").write_text("""# Summary 1
Key points and overview
--==SUMMARY==--
Important summary content
""")

    (test_files["input_dir"] / "notes1.md").write_text("""# Notes 1
Detailed notes
--==RAW NOTES==--
Raw note content
""")

    (test_files["input_dir"] / "attachment1.md").write_text("""# Attachment 1
--==ATTACHMENTS==--
[File 1](files/doc1.pdf)
![Image 1](images/img1.png)
""")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    output_file = test_files["output_dir"] / "all_merged_markdown.md"
    content = output_file.read_text()
    
    # Check metadata preservation
    assert '"processor": "MetadataManager"' in content
    assert '"version": "1.0"' in content
    assert 'summary1.md' in content
    assert 'notes1.md' in content
    assert 'attachment1.md' in content
    assert 'Important summary content' in content
    assert 'Raw note content' in content
    assert '[File 1](files/doc1.pdf)' in content

async def test_relationship_preservation(processor, test_files):
    """Test preservation of relationships between files and attachments."""
    # Create test files with different content types
    (test_files["input_dir"] / "summary1.md").write_text("""# Summary 1
Key points and overview
--==SUMMARY==--
Important summary content
""")

    (test_files["input_dir"] / "notes1.md").write_text("""# Notes 1
Detailed notes
--==RAW NOTES==--
Raw note content
""")

    (test_files["input_dir"] / "attachment1.md").write_text("""# Attachment 1
--==ATTACHMENTS==--
[File 1](files/doc1.pdf)
![Image 1](images/img1.png)
""")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    output_file = test_files["output_dir"] / "all_merged_markdown.md"
    content = output_file.read_text()
    
    # Check relationship tracking
    assert '"type": "link"' in content
    assert '"source": "attachment1.md"' in content
    assert '"target": "files/doc1.pdf"' in content
    assert '"type": "image"' in content
    assert 'images/img1.png' in content

async def test_section_organization(processor, test_files):
    """Test metadata-based content organization."""
    # Create test files with different content types
    (test_files["input_dir"] / "summary1.md").write_text("""# Summary 1
Key points and overview
--==SUMMARY==--
Important summary content
""")

    (test_files["input_dir"] / "notes1.md").write_text("""# Notes 1
Detailed notes
--==RAW NOTES==--
Raw note content
""")

    (test_files["input_dir"] / "attachment1.md").write_text("""# Attachment 1
--==ATTACHMENTS==--
[File 1](files/doc1.pdf)
![Image 1](images/img1.png)
""")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    output_file = test_files["output_dir"] / "all_merged_markdown.md"
    content = output_file.read_text()
    
    # Check section organization
    summary_pos = content.find("Important summary content")
    notes_pos = content.find("Raw note content")
    attachments_pos = content.find("[File 1](files/doc1.pdf)")
    
    assert summary_pos < notes_pos < attachments_pos
    assert "--==SUMMARY==--" in content
    assert "--==RAW NOTES==--" in content
    assert "--==ATTACHMENTS==--" in content

async def test_metadata_merging(processor, test_files):
    """Test merging of metadata from multiple files."""
    # Create first file with metadata
    file1_content = """<!-- {
        "document": {
            "file": "file1.md",
            "timestamp": "2023-12-26T12:00:00"
        },
        "relationships": {
            "attachments": [
                {"type": "image", "path": "img1.png"}
            ]
        }
    } -->
    
    Content from file 1
    ![Image 1](img1.png)
    """
    (test_files["input_dir"] / "file1.md").write_text(file1_content)
    
    # Create second file with metadata
    file2_content = """<!-- {
        "document": {
            "file": "file2.md",
            "timestamp": "2023-12-26T12:01:00"
        },
        "relationships": {
            "attachments": [
                {"type": "image", "path": "img2.png"}
            ]
        }
    } -->
    
    Content from file 2
    ![Image 2](img2.png)
    """
    (test_files["input_dir"] / "file2.md").write_text(file2_content)
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    output_file = test_files["output_dir"] / "all_merged_markdown.md"
    content = output_file.read_text()
    
    # Check merged metadata
    assert 'file1.md' in content
    assert 'file2.md' in content
    assert 'img1.png' in content
    assert 'img2.png' in content
    assert '"total_files": 2' in content

async def test_path_updates(processor, test_files):
    """Test updating of relative paths in content."""
    # Create nested directory structure
    subdir = test_files["input_dir"] / "subdir"
    subdir.mkdir()
    image_dir = subdir / "images"
    image_dir.mkdir()
    
    # Create image file
    (image_dir / "test.png").write_text("dummy image")
    
    # Create document with relative path
    doc_content = """<!-- {
        "document": {
            "file": "subdir/doc.md"
        }
    } -->
    
    # Document
    ![Image](images/test.png)
    """
    (subdir / "doc.md").write_text(doc_content)
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    output_file = test_files["output_dir"] / "all_merged_markdown.md"
    content = output_file.read_text()
    
    # Check path updates
    assert 'subdir/images/test.png' in content 