"""Tests for markdown parse phase."""

import pytest
from pathlib import Path
import base64
import shutil
import os
import json
from PIL import Image
import io
from docx import Document

from nova.phases.parse.handlers.markdown import MarkdownHandler
from nova.phases.parse.handlers.markdown.document_converter import DocumentConverter
from nova.phases.parse.handlers.markdown.image_converter import ImageConverter

@pytest.fixture
def test_dir(tmp_path):
    """Create test directory with sample files."""
    # Create test files
    test_dir = tmp_path / "test_files"
    test_dir.mkdir()
    
    # Create sample markdown file
    md_content = """# Test Document

This is a test document with various attachments.

## Images
![Local Image](images/test.jpg)
![HEIC Image](images/photo.heic)
![Base64 Image](data:image/png;base64,{})

## Documents
[Word Document](docs/test.docx)
[PDF Document](docs/test.pdf)
[Excel Sheet](docs/test.xlsx)
"""
    
    # Create sample image and encode as base64
    img = Image.new('RGB', (100, 100), color='red')
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    img_base64 = base64.b64encode(img_bytes.getvalue()).decode()
    
    # Write markdown with base64 image
    md_file = test_dir / "test.md"
    md_file.write_text(md_content.format(img_base64))
    
    # Create sample image files
    img_dir = test_dir / "images"
    img_dir.mkdir()
    img.save(img_dir / "test.jpg")
    
    # Create sample HEIC image
    heic_img = Image.new('RGB', (100, 100), color='blue')
    heic_bytes = io.BytesIO()
    heic_img.save(heic_bytes, format='JPEG')  # Save as JPEG since we can't create HEIC directly
    (img_dir / "photo.heic").write_bytes(heic_bytes.getvalue())
    
    # Create sample documents
    doc_dir = test_dir / "docs"
    doc_dir.mkdir()
    (doc_dir / "test.docx").write_text("Sample Word document")
    (doc_dir / "test.pdf").write_text("Sample PDF document")
    (doc_dir / "test.xlsx").write_text("Sample Excel document")
    
    return test_dir

@pytest.mark.asyncio
async def test_markdown_processing(tmp_path, test_dir):
    """Test markdown processing with various attachments."""
    # Set up handler
    handler = MarkdownHandler({
        'document_conversion': True,
        'image_processing': True,
        'metadata_preservation': True
    })
    
    # Set up output directory
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Process markdown file
    md_file = test_dir / "test.md"
    result = await handler.process(
        md_file,
        {
            'output_dir': str(output_dir),
            'file_stem': md_file.stem
        }
    )
    
    # Check for errors
    assert not result.errors, f"Processing failed with errors: {result.errors}"
    
    # Check output structure
    output_md = output_dir / "test.md"
    assert output_md.exists()
    
    md_dir = output_dir / "test"
    assert md_dir.exists()
    
    # Verify content
    content = output_md.read_text()
    
    # Check image references
    assert "test/test.jpg" in content
    assert "test/photo.jpeg" in content  # HEIC should be converted to JPG
    assert "test/image_" in content and ".png" in content  # Base64 image
    assert "data:image/png;base64" not in content  # Base64 should be extracted
    
    # Check document references
    assert "test/test.docx" in content
    assert "test/test.pdf" in content
    assert "test/test.xlsx" in content
    
    # Check metadata
    assert "<!-- {" in content and "}" in content
    
    # Check files in markdown directory
    files = list(md_dir.glob("*"))
    assert len(files) >= 6  # All attachments should be copied/converted
    
    # Verify HEIC conversion
    heic_files = list(md_dir.glob("*.heic"))
    assert not heic_files  # No HEIC files should remain
    jpg_files = list(md_dir.glob("*.jpg"))
    assert jpg_files  # Should have JPG files

@pytest.mark.asyncio
async def test_document_converter():
    """Test document conversion."""
    converter = DocumentConverter()
    
    # Create test document using python-docx
    doc = Document()
    doc_content = "Test document content"
    doc.add_paragraph(doc_content)
    
    # Save document
    doc_file = Path("test.docx")
    doc.save(doc_file)
    
    try:
        # Convert document
        result = await converter.convert_to_markdown(doc_file)
        assert result.success
        assert doc_content in result.content
        assert result.metadata['converter'] == 'DocxConverter'
    finally:
        doc_file.unlink()

@pytest.mark.asyncio
async def test_image_converter():
    """Test image conversion."""
    converter = ImageConverter()
    
    # Create test image
    img = Image.new('RGB', (100, 100), color='red')
    img_file = Path("test.heic")
    img.save(img_file, format='JPEG')  # Save as JPEG since we can't create HEIC directly
    
    try:
        # Convert image
        result = await converter.convert_image(img_file)
        assert result.success
        assert result.format == 'jpeg'
        assert result.dimensions == (100, 100)
        assert result.metadata['original_format'] == 'JPEG'
        assert result.metadata['target_format'] == 'JPEG'
    finally:
        img_file.unlink() 