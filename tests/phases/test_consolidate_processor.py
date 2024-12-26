"""Test cases for markdown consolidate processor."""

import pytest
from pathlib import Path
import shutil
import os
from typing import Dict, Any

from nova.phases.consolidate.processor import MarkdownConsolidateProcessor
from nova.core.config import ProcessorConfig, PipelineConfig, PathConfig

@pytest.fixture
def test_files(tmp_path):
    """Create test files and directories."""
    # Create test directories
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    processing_dir = input_dir / "processing"
    temp_dir = input_dir / "temp"
    
    # Create all directories
    input_dir.mkdir(parents=True)
    output_dir.mkdir(parents=True)
    processing_dir.mkdir(parents=True)
    temp_dir.mkdir(parents=True)
    
    # Create test markdown files
    (input_dir / "doc1.md").write_text("# Doc 1\nContent 1")
    (input_dir / "doc2.md").write_text("# Doc 2\nContent 2")
    
    # Create nested directory with files
    nested_dir = input_dir / "nested"
    nested_dir.mkdir()
    (nested_dir / "nested_doc.md").write_text("# Nested Doc\nNested Content")
    
    # Create attachment directory
    attachment_dir = input_dir / "doc1"
    attachment_dir.mkdir()
    (attachment_dir / "image.png").write_bytes(b"fake image data")
    (attachment_dir / "doc.pdf").write_bytes(b"fake pdf data")
    
    return {
        "input_dir": input_dir,
        "output_dir": output_dir,
        "processing_dir": processing_dir,
        "temp_dir": temp_dir
    }

@pytest.fixture
def processor(test_files):
    """Create processor instance with test configuration."""
    config = ProcessorConfig(
        name="markdown_consolidate",
        description="Consolidate markdown files and attachments",
        processor="MarkdownConsolidateProcessor",
        output_dir=str(test_files["output_dir"]),
        options={
            "preserve_structure": True,
            "handle_attachments": True
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
    os.environ["NOVA_PHASE_MARKDOWN_PARSE"] = str(test_files["input_dir"])
    os.environ["NOVA_PHASE_MARKDOWN_CONSOLIDATE"] = str(test_files["output_dir"])
    
    return MarkdownConsolidateProcessor(config, pipeline_config)

@pytest.fixture
def pipeline_config(tmp_path):
    """Create a basic pipeline configuration for testing."""
    return PipelineConfig(
        paths=PathConfig(
            base_dir=str(tmp_path)
        ),
        phases=[
            ProcessorConfig(
                name="MARKDOWN_CONSOLIDATE",
                description="Consolidate markdown files",
                output_dir=str(tmp_path / "output"),
                processor="MarkdownConsolidateProcessor",
                input_dir=str(tmp_path / "input")
            )
        ],
        input_dir=str(tmp_path / "input"),
        output_dir=str(tmp_path / "output"),
        processing_dir=str(tmp_path / "processing"),
        temp_dir=str(tmp_path / "temp")
    )

# Hero Test Cases

async def test_basic_consolidation(processor, test_files):
    """Test basic consolidation of markdown files."""
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Check output files exist
    assert (test_files["output_dir"] / "doc1.md").exists()
    assert (test_files["output_dir"] / "doc2.md").exists()
    assert (test_files["output_dir"] / "nested" / "nested_doc.md").exists()

async def test_attachment_handling(processor, test_files):
    """Test handling of attachments during consolidation."""
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Check attachment directory exists
    attachment_dir = test_files["output_dir"] / "doc1"
    assert attachment_dir.exists()
    assert (attachment_dir / "image.png").exists()
    assert (attachment_dir / "doc.pdf").exists()
    
    # Check references in markdown
    content = (test_files["output_dir"] / "doc1.md").read_text()
    assert "image.png" in content
    assert "doc.pdf" in content

async def test_metadata_preservation(processor, test_files):
    """Test preservation of metadata during consolidation."""
    # Create file with frontmatter
    frontmatter = """---
title: Test Document
author: Test User
date: 2024-01-01
---
# Content
Test content
"""
    (test_files["input_dir"] / "with_meta.md").write_text(frontmatter)
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Check metadata preserved
    output_content = (test_files["output_dir"] / "with_meta.md").read_text()
    assert "title: Test Document" in output_content
    assert "author: Test User" in output_content

# Edge Cases

async def test_empty_files(processor, test_files):
    """Test handling of empty files."""
    # Create empty files
    (test_files["input_dir"] / "empty.md").write_text("")
    (test_files["input_dir"] / "whitespace.md").write_text("   \n  \n  ")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Check empty files handled
    assert (test_files["output_dir"] / "empty.md").exists()
    assert (test_files["output_dir"] / "whitespace.md").exists()

async def test_special_characters(processor, test_files):
    """Test handling of files with special characters."""
    # Create files with special characters
    special_file = test_files["input_dir"] / "special_$#@!.md"
    special_file.write_text("Special content")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Check special character file handled
    assert (test_files["output_dir"] / "special_$#@!.md").exists()

async def test_broken_frontmatter(processor, test_files):
    """Test handling of files with broken frontmatter."""
    broken_frontmatter = """---
title: Broken
invalid yaml:
  - unclosed quote: "test
---
Content
"""
    (test_files["input_dir"] / "broken_meta.md").write_text(broken_frontmatter)
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Should still process file despite broken frontmatter
    assert (test_files["output_dir"] / "broken_meta.md").exists()

async def test_missing_attachment_dir(processor, test_files):
    """Test handling of referenced attachments with missing directory."""
    content = """# Test
![Missing Image](missing/image.png)
[Missing Doc](missing/doc.pdf)
"""
    (test_files["input_dir"] / "missing_attachments.md").write_text(content)
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Should process file but log warnings about missing attachments
    assert (test_files["output_dir"] / "missing_attachments.md").exists()

async def test_circular_references(processor, test_files):
    """Test handling of circular references between files."""
    # Create files that reference each other
    (test_files["input_dir"] / "circular1.md").write_text("[Link to 2](circular2.md)")
    (test_files["input_dir"] / "circular2.md").write_text("[Link to 1](circular1.md)")
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Both files should be processed
    assert (test_files["output_dir"] / "circular1.md").exists()
    assert (test_files["output_dir"] / "circular2.md").exists()

async def test_large_file_handling(processor, test_files):
    """Test handling of large files."""
    # Create a large file (5MB)
    large_content = "Large content\n" * 500000
    (test_files["input_dir"] / "large_file.md").write_text(large_content)
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Large file should be processed
    assert (test_files["output_dir"] / "large_file.md").exists()
    assert (test_files["output_dir"] / "large_file.md").stat().st_size > 5000000

async def test_unicode_content(processor, test_files):
    """Test handling of unicode content."""
    unicode_content = """# Unicode Test
Chinese: 你好世界
Japanese: こんにちは世界
Emoji: 🌍🌎🌏
"""
    (test_files["input_dir"] / "unicode.md").write_text(unicode_content)
    
    await processor.setup()
    success = await processor.process()
    assert success
    
    # Check unicode preserved
    output_content = (test_files["output_dir"] / "unicode.md").read_text()
    assert "你好世界" in output_content
    assert "こんにちは世界" in output_content
    assert "🌍🌎🌏" in output_content 