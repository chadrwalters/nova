"""Tests for the aggregate handler."""

import pytest
from pathlib import Path
import tempfile
import os
import shutil
from typing import Dict, Any

from nova.phases.aggregate.handlers.aggregate_handler import AggregateHandler
from nova.core.models.result import ProcessingResult


@pytest.fixture
def test_files():
    """Create test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create input directory
        input_dir = Path(temp_dir) / "input"
        input_dir.mkdir()
        
        # Create output directory
        output_dir = Path(temp_dir) / "output"
        output_dir.mkdir()
        
        # Create test markdown files
        test_md1 = input_dir / "test1.md"
        test_md1.write_text("""# First Document

This is the first test document.
""")
        
        test_md2 = input_dir / "test2.md"
        test_md2.write_text("""# Second Document

This is the second test document.
""")
        
        test_md3 = input_dir / "test3.md"
        test_md3.write_text("""Third Document
==============

This is the third test document.
""")
        
        yield {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "test_md1": test_md1,
            "test_md2": test_md2,
            "test_md3": test_md3
        }


@pytest.fixture
def handler(test_files):
    """Create handler instance with test configuration."""
    config = {
        "output_dir": str(test_files["output_dir"]),
        "output_filename": "merged.md"
    }
    return AggregateHandler(config)


@pytest.mark.asyncio
async def test_can_handle(handler, test_files):
    """Test file type detection."""
    # Test markdown file
    assert await handler.can_handle(test_files["test_md1"])
    
    # Test non-existent file
    non_existent = test_files["input_dir"] / "nonexistent.md"
    assert not await handler.can_handle(non_existent)
    assert handler.monitoring.metrics["errors"] > 0
    assert len(handler.state.errors) > 0


@pytest.mark.asyncio
async def test_extract_title(handler, test_files):
    """Test title extraction."""
    # Test ATX-style header
    content = test_files["test_md1"].read_text()
    title = handler._extract_title(content)
    assert title == "First Document"
    
    # Test Setext-style header
    content = test_files["test_md3"].read_text()
    title = handler._extract_title(content)
    assert title == "Third Document"
    
    # Test no title
    content = "No title here\nJust content"
    title = handler._extract_title(content)
    assert title is None


@pytest.mark.asyncio
async def test_generate_toc(handler):
    """Test table of contents generation."""
    sections = [
        {"filename": "test1", "title": "First Document"},
        {"filename": "test2", "title": "Second Document"},
        {"filename": "test3", "title": None}
    ]
    
    toc = handler._generate_toc(sections)
    
    assert "# Table of Contents" in toc
    assert "1. [First Document](#test1)" in toc
    assert "2. [Second Document](#test2)" in toc
    assert "3. [Section 3](#test3)" in toc


@pytest.mark.asyncio
async def test_add_navigation(handler):
    """Test navigation link addition."""
    content = "# Test Content"
    
    # Test with both links
    result = handler._add_navigation(
        content,
        "[Prev](#prev)",
        "[Next](#next)"
    )
    assert "[Prev](#prev)" in result
    assert "[Next](#next)" in result
    assert "[↑ Back to Top](#table-of-contents)" in result
    
    # Test with only prev
    result = handler._add_navigation(content, "[Prev](#prev)")
    assert "[Prev](#prev)" in result
    assert "[Next](#next)" not in result
    
    # Test with only next
    result = handler._add_navigation(content, next_link="[Next](#next)")
    assert "[Prev](#prev)" not in result
    assert "[Next](#next)" in result


@pytest.mark.asyncio
async def test_process_markdown(handler, test_files):
    """Test processing markdown files."""
    files = [
        test_files["test_md1"],
        test_files["test_md2"],
        test_files["test_md3"]
    ]
    
    result = await handler.process(files)
    
    assert result.success
    assert result.content
    assert result.metadata
    
    # Check output file exists
    output_file = Path(result.content)
    assert output_file.exists()
    
    # Check content
    content = output_file.read_text()
    assert "# Table of Contents" in content
    assert "# First Document" in content
    assert "# Second Document" in content
    assert "Third Document" in content
    assert "==============" in content
    
    # Check section markers
    assert handler.section_markers["start"].format(filename="test1") in content
    assert handler.section_markers["start"].format(filename="test2") in content
    assert handler.section_markers["start"].format(filename="test3") in content
    
    # Check navigation
    assert "← Previous:" in content
    assert "Next:" in content
    assert "[↑ Back to Top](#table-of-contents)" in content
    
    # Check metadata
    assert result.metadata["output_path"] == str(output_file)
    assert len(result.metadata["sections"]) == 3
    assert result.metadata["sections"][0]["title"] == "First Document"
    assert result.metadata["sections"][1]["title"] == "Second Document"
    assert result.metadata["sections"][2]["title"] == "Third Document"
    assert result.metadata["metrics"]["files_processed"] == 3
    assert result.metadata["metrics"]["content_size"] > 0


@pytest.mark.asyncio
async def test_process_no_files(handler):
    """Test processing with no files."""
    result = await handler.process([])
    
    assert not result.success
    assert "No files to process" in result.errors[0]
    assert handler.monitoring.metrics["errors"] > 0


@pytest.mark.asyncio
async def test_process_no_output_dir():
    """Test processing without output directory."""
    handler = AggregateHandler()  # No config
    
    with tempfile.NamedTemporaryFile(suffix='.md') as temp_file:
        result = await handler.process([Path(temp_file.name)])
        
        assert not result.success
        assert "No output directory specified" in result.errors[0]
        assert handler.monitoring.metrics["errors"] > 0


def test_validation():
    """Test result validation."""
    handler = AggregateHandler()
    
    valid_result = ProcessingResult(
        success=True,
        processed_files=["test.md"],
        content="# Test\nContent",
        metadata={"title": "Test"}
    )
    assert handler.validate(valid_result)
    
    invalid_result = ProcessingResult(
        success=False,
        processed_files=[],
        content=None,
        metadata={}
    )
    assert not handler.validate(invalid_result) 