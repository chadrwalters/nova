#!/usr/bin/env python3

import os
import pytest
from pathlib import Path
from markdown_processor import MarkdownProcessor
from PIL import Image
from PyPDF2 import PdfWriter, PdfReader
from io import BytesIO
from reportlab.pdfgen import canvas

@pytest.fixture
def setup_dirs(tmp_path):
    """Set up test directories."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    temp_dir = tmp_path / "temp"
    
    input_dir.mkdir()
    output_dir.mkdir()
    temp_dir.mkdir()
    
    return input_dir, output_dir, temp_dir

@pytest.fixture
def create_test_files(setup_dirs):
    """Create test markdown files and attachments."""
    input_dir, _, _ = setup_dirs
    
    # Create a test markdown file
    md_file = input_dir / "test.md"
    md_content = """# Test Document

This is a test document with an image and a link.

![Test Image](test_image.jpg)

[Test Document](test_doc.pdf)
"""
    md_file.write_text(md_content)
    
    # Create a test image
    img_file = input_dir / "test_image.jpg"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_file)
    
    # Create a test PDF with actual content
    pdf_file = input_dir / "test_doc.pdf"
    packet = BytesIO()
    can = canvas.Canvas(packet)
    can.drawString(10, 100, "Test PDF Content")
    can.save()
    
    # Move to the beginning of the StringIO buffer
    packet.seek(0)
    new_pdf = PdfReader(packet)
    
    # Create the PDF writer
    writer = PdfWriter()
    writer.add_page(new_pdf.pages[0])
    
    # Add some metadata
    writer.add_metadata({
        '/Title': 'Test Document',
        '/Author': 'Test Author'
    })
    
    # Save the PDF
    with open(pdf_file, 'wb') as f:
        writer.write(f)
    
    return md_file, img_file, pdf_file

def test_processor_initialization(setup_dirs):
    """Test markdown processor initialization."""
    input_dir, output_dir, temp_dir = setup_dirs
    processor = MarkdownProcessor(input_dir, output_dir, temp_dir)
    
    assert processor.input_dir == input_dir
    assert processor.output_dir == output_dir
    assert processor.temp_dir == temp_dir
    assert processor.md is not None

def test_file_processing(setup_dirs, create_test_files):
    """Test processing a single markdown file."""
    input_dir, output_dir, temp_dir = setup_dirs
    md_file, _, _ = create_test_files
    
    processor = MarkdownProcessor(input_dir, output_dir, temp_dir)
    result = processor.process_file(md_file)
    
    assert result is not None
    assert result['input_file'] == str(md_file)
    assert result['output_file'] == str(output_dir / "test.md")
    assert len(result['attachments']) == 2  # One image and one PDF
    
    # Check that output file exists
    output_file = Path(result['output_file'])
    assert output_file.exists()
    
    # Check output content
    content = output_file.read_text()
    assert "--==ATTACHMENT_BLOCK:" in content
    assert "--==ATTACHMENT_BLOCK_END==--" in content

def test_directory_processing(setup_dirs, create_test_files):
    """Test processing all markdown files in a directory."""
    input_dir, output_dir, temp_dir = setup_dirs
    
    processor = MarkdownProcessor(input_dir, output_dir, temp_dir)
    success = processor.process_directory()
    
    assert success
    assert (output_dir / "test.md").exists()

def test_invalid_file_handling(setup_dirs):
    """Test handling of invalid files."""
    input_dir, output_dir, temp_dir = setup_dirs
    
    # Create an invalid markdown file
    invalid_file = input_dir / "invalid.md"
    invalid_file.write_bytes(b"\x80\x81")  # Invalid UTF-8
    
    processor = MarkdownProcessor(input_dir, output_dir, temp_dir)
    result = processor.process_file(invalid_file)
    
    assert result is None

def test_missing_attachment_handling(setup_dirs):
    """Test handling of missing attachments."""
    input_dir, output_dir, temp_dir = setup_dirs
    
    # Create markdown file with missing attachment
    md_file = input_dir / "missing.md"
    md_content = "![Missing Image](missing.jpg)"
    md_file.write_text(md_content)
    
    processor = MarkdownProcessor(input_dir, output_dir, temp_dir)
    result = processor.process_file(md_file)
    
    assert result is not None
    assert len(result['attachments']) == 0

def test_nested_directory_processing(setup_dirs):
    """Test processing markdown files in nested directories."""
    input_dir, output_dir, temp_dir = setup_dirs
    
    # Create nested directory structure
    nested_dir = input_dir / "nested" / "dir"
    nested_dir.mkdir(parents=True)
    
    # Create markdown file in nested directory
    md_file = nested_dir / "nested.md"
    md_content = "# Nested Test"
    md_file.write_text(md_content)
    
    processor = MarkdownProcessor(input_dir, output_dir, temp_dir)
    success = processor.process_directory()
    
    assert success
    assert (output_dir / "nested" / "dir" / "nested.md").exists()

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 