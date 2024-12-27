"""Tests for the consolidation handler."""

import pytest
from pathlib import Path
import tempfile
import os
import shutil
from typing import Dict, Any

from nova.phases.consolidate.handlers.consolidation_handler import ConsolidationHandler
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
        test_md.write_text("""# Test Document
        
This is a test document with an image:
![Test Image](images/test.png)

And a link:
[Test Link](docs/test.pdf)
""")
        
        # Create test image
        image_dir = input_dir / "images"
        image_dir.mkdir()
        test_image = image_dir / "test.png"
        test_image.write_bytes(b'test image content')
        
        # Create test document
        doc_dir = input_dir / "docs"
        doc_dir.mkdir()
        test_doc = doc_dir / "test.pdf"
        test_doc.write_bytes(b'test document content')
        
        yield {
            "input_dir": input_dir,
            "output_dir": output_dir,
            "test_md": test_md,
            "test_image": test_image,
            "test_doc": test_doc
        }


@pytest.fixture
def handler(test_files):
    """Create handler instance with test configuration."""
    config = {
        "output_dir": str(test_files["output_dir"])
    }
    return ConsolidationHandler(config)


@pytest.mark.asyncio
async def test_can_handle(handler, test_files):
    """Test file type detection."""
    # Test markdown file
    assert await handler.can_handle(test_files["test_md"])
    
    # Test non-markdown file
    assert not await handler.can_handle(test_files["test_image"])
    
    # Test non-existent file
    non_existent = test_files["input_dir"] / "nonexistent.md"
    assert not await handler.can_handle(non_existent)
    assert handler.monitoring.metrics["errors"] > 0
    assert len(handler.state.errors) > 0


@pytest.mark.asyncio
async def test_find_attachments(handler, test_files):
    """Test finding attachments in markdown content."""
    content = test_files["test_md"].read_text()
    attachments = handler._find_attachments(content)
    
    assert len(attachments) == 2
    assert "images/test.png" in attachments
    assert "docs/test.pdf" in attachments


@pytest.mark.asyncio
async def test_copy_attachment(handler, test_files):
    """Test copying attachments."""
    # Test valid attachment
    new_path = handler._copy_attachment(
        "images/test.png",
        test_files["input_dir"],
        test_files["output_dir"]
    )
    assert new_path is not None
    assert (test_files["output_dir"] / "images/test.png").exists()
    
    # Test non-existent attachment
    new_path = handler._copy_attachment(
        "nonexistent.png",
        test_files["input_dir"],
        test_files["output_dir"]
    )
    assert new_path is None
    assert handler.monitoring.metrics["errors"] > 0
    assert len(handler.state.errors) > 0


def test_find_attachments():
    """Test finding attachments in content."""
    handler = ConsolidationHandler()
    content = "![image](attachments/image.png)\n[doc](attachments/doc.pdf)"
    attachments = handler._find_attachments(content)
    assert "attachments/image.png" in attachments
    assert "attachments/doc.pdf" in attachments


def test_validation():
    """Test result validation."""
    handler = ConsolidationHandler()
    
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