"""Tests for the split handler."""

import pytest
from pathlib import Path
import tempfile
import os
import shutil
from typing import Dict, Any

from nova.phases.split.handlers.split_handler import SplitHandler
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
        
        # Create test markdown file
        test_md = input_dir / "test.md"
        test_md.write_text("""--==SUMMARY==--
# Summary

This is the summary section.

--==RAW NOTES==--
# Raw Notes

These are the raw notes.

--==ATTACHMENTS==--
# Attachments

- ![Image](images/test.png)
- [Document](docs/test.pdf)
""")
        
        yield {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "test_md": test_md
        }


@pytest.fixture
def handler(test_files):
    """Create handler instance with test configuration."""
    config = {
        "output_dir": str(test_files["output_dir"])
    }
    return SplitHandler(config)


@pytest.mark.asyncio
async def test_can_handle(handler, test_files):
    """Test file type detection."""
    # Test markdown file
    assert await handler.can_handle(test_files["test_md"])
    
    # Test non-existent file
    non_existent = test_files["input_dir"] / "nonexistent.md"
    assert not await handler.can_handle(non_existent)
    assert handler.monitoring.metrics["errors"] > 0
    assert len(handler.state.errors) > 0


@pytest.mark.asyncio
async def test_split_content(handler, test_files):
    """Test content splitting."""
    content = test_files["test_md"].read_text()
    summary, raw_notes, attachments = handler._split_content(content)
    
    assert "# Summary" in summary
    assert "This is the summary section" in summary
    assert "# Raw Notes" in raw_notes
    assert "These are the raw notes" in raw_notes
    assert "# Attachments" in attachments
    assert "![Image](images/test.png)" in attachments
    assert "[Document](docs/test.pdf)" in attachments


@pytest.mark.asyncio
async def test_add_cross_links(handler):
    """Test cross-link addition."""
    content = "# Test Content"
    
    # Test summary section
    result = handler._add_cross_links(content, "summary")
    assert "[Raw Notes](raw_notes.md)" in result
    assert "[Attachments](attachments.md)" in result
    assert "[Summary](summary.md)" not in result
    
    # Test raw notes section
    result = handler._add_cross_links(content, "raw_notes")
    assert "[Summary](summary.md)" in result
    assert "[Attachments](attachments.md)" in result
    assert "[Raw Notes](raw_notes.md)" not in result
    
    # Test attachments section
    result = handler._add_cross_links(content, "attachments")
    assert "[Summary](summary.md)" in result
    assert "[Raw Notes](raw_notes.md)" in result
    assert "[Attachments](attachments.md)" not in result


@pytest.mark.asyncio
async def test_write_section(handler, test_files):
    """Test section writing."""
    content = "# Test Section\n\nTest content."
    output_path = handler._write_section(content, "summary")
    
    assert output_path.exists()
    assert output_path.name == "summary.md"
    
    # Check content
    written_content = output_path.read_text()
    assert "# Test Section" in written_content
    assert "Test content" in written_content
    assert "[Raw Notes](raw_notes.md)" in written_content
    assert "[Attachments](attachments.md)" in written_content


def test_add_cross_links():
    """Test adding cross-links between sections."""
    handler = SplitHandler()
    content = "# Test\nContent"
    links = {
        "summary": "summary.md",
        "raw_notes": "raw_notes.md",
        "attachments": "attachments.md"
    }
    linked = handler._add_cross_links(content, links)
    assert "[Summary](summary.md)" in linked
    assert "[Raw Notes](raw_notes.md)" in linked
    assert "[Attachments](attachments.md)" in linked


def test_validation():
    """Test result validation."""
    handler = SplitHandler()
    
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