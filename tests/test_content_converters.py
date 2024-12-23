"""Tests for content converters."""

import os
import json
from pathlib import Path
import pytest
from bs4 import BeautifulSoup
import pandas as pd
from PIL import Image
import yaml
import fitz

from nova.processors.components.content_converters import (
    ContentConverterFactory,
    HTMLConverter,
    CSVConverter,
    JSONConverter,
    TextConverter,
    OfficeConverter,
    PDFConverter,
    ImageConverter
)
from nova.core.errors import ProcessingError

# Test fixtures directory
FIXTURES_DIR = Path(__file__).parent / "fixtures" / "attachments"

@pytest.fixture
def html_file(tmp_path):
    """Create a test HTML file."""
    content = """
    <html>
        <head>
            <title>Test Document</title>
        </head>
        <body>
            <h1>Test Heading</h1>
            <p>Test paragraph</p>
            <table>
                <tr><th>Header 1</th><th>Header 2</th></tr>
                <tr><td>Cell 1</td><td>Cell 2</td></tr>
            </table>
        </body>
    </html>
    """
    file_path = tmp_path / "test.html"
    file_path.write_text(content)
    return file_path

@pytest.fixture
def csv_file(tmp_path):
    """Create a test CSV file."""
    content = "Name,Age,City\nJohn,30,New York\nJane,25,London"
    file_path = tmp_path / "test.csv"
    file_path.write_text(content)
    return file_path

@pytest.fixture
def json_file(tmp_path):
    """Create a test JSON file."""
    content = {
        "name": "Test",
        "values": [1, 2, 3],
        "nested": {"key": "value"}
    }
    file_path = tmp_path / "test.json"
    file_path.write_text(json.dumps(content))
    return file_path

@pytest.fixture
def text_file(tmp_path):
    """Create a test text file."""
    content = "Line 1\nLine 2\nLine 3"
    file_path = tmp_path / "test.txt"
    file_path.write_text(content)
    return file_path

@pytest.fixture
def yaml_file(tmp_path):
    """Create a test YAML file."""
    content = """
    name: Test
    values:
      - 1
      - 2
      - 3
    nested:
      key: value
    """
    file_path = tmp_path / "test.yaml"
    file_path.write_text(content)
    return file_path

@pytest.fixture
def converter_factory():
    """Create a converter factory instance."""
    return ContentConverterFactory()

def test_html_converter(html_file):
    """Test HTML to markdown conversion."""
    converter = HTMLConverter()
    content, metadata = converter.convert(html_file)
    
    assert "# Test Document" in content
    assert "Test Heading" in content
    assert "Test paragraph" in content
    assert "| Header 1 | Header 2 |" in content
    assert "| Cell 1 | Cell 2 |" in content
    
    assert metadata["title"] == "Test Document"
    assert metadata["tables"] == 1
    assert metadata["original_format"] == "html"

def test_csv_converter(csv_file):
    """Test CSV to markdown conversion."""
    converter = CSVConverter()
    content, metadata = converter.convert(csv_file)
    
    assert "| Name | Age | City |" in content
    assert "| John | 30 | New York |" in content
    assert "| Jane | 25 | London |" in content
    
    assert metadata["rows"] == 2
    assert metadata["columns"] == 3
    assert metadata["original_format"] == "csv"

def test_json_converter(json_file):
    """Test JSON to markdown conversion."""
    converter = JSONConverter()
    content, metadata = converter.convert(json_file)
    
    assert "```json" in content
    assert '"name": "Test"' in content
    assert '"values": [' in content
    assert '1,' in content
    assert '2,' in content
    assert '3' in content
    assert ']' in content
    
    assert metadata["original_format"] == "json"
    assert "top_level_keys" in metadata
    assert "name" in metadata["top_level_keys"]

def test_text_converter(text_file):
    """Test text to markdown conversion."""
    converter = TextConverter()
    content, metadata = converter.convert(text_file)
    
    # The content might be detected as YAML or text
    assert any(x in content for x in ["```text", "```yaml"])
    assert "Line 1" in content
    assert "Line 2" in content
    assert "Line 3" in content
    
    assert metadata["original_format"] == "text"
    assert metadata["lines"] == 3
    assert metadata["characters"] > 0

def test_yaml_detection(yaml_file):
    """Test YAML detection in text converter."""
    converter = TextConverter()
    content, metadata = converter.convert(yaml_file)
    
    assert "```yaml" in content
    assert "name: Test" in content
    assert metadata["detected_format"] == "yaml"

def test_converter_factory_file_types(converter_factory, tmp_path):
    """Test converter factory file type detection."""
    # Create test files
    (tmp_path / "test.html").touch()
    (tmp_path / "test.csv").touch()
    (tmp_path / "test.json").touch()
    (tmp_path / "test.txt").touch()
    (tmp_path / "test.docx").touch()
    (tmp_path / "test.pdf").touch()
    (tmp_path / "test.jpg").touch()
    
    # Test converter selection
    assert isinstance(converter_factory.get_converter(tmp_path / "test.html"), HTMLConverter)
    assert isinstance(converter_factory.get_converter(tmp_path / "test.csv"), CSVConverter)
    assert isinstance(converter_factory.get_converter(tmp_path / "test.json"), JSONConverter)
    assert isinstance(converter_factory.get_converter(tmp_path / "test.txt"), TextConverter)
    assert isinstance(converter_factory.get_converter(tmp_path / "test.docx"), OfficeConverter)
    assert isinstance(converter_factory.get_converter(tmp_path / "test.pdf"), PDFConverter)
    assert isinstance(converter_factory.get_converter(tmp_path / "test.jpg"), ImageConverter)

def test_converter_factory_unsupported_type(converter_factory, tmp_path):
    """Test converter factory with unsupported file type."""
    test_file = tmp_path / "test.unsupported"
    test_file.touch()
    
    with pytest.raises(ProcessingError, match="No converter available for file type"):
        converter_factory.get_converter(test_file)

def test_converter_factory_wrap_with_markers(converter_factory, tmp_path):
    """Test wrapping content with attachment markers."""
    content = "Test content"
    file_path = tmp_path / "test.txt"
    
    wrapped = converter_factory.wrap_with_markers(content, file_path)
    
    assert "--==ATTACHMENT_BLOCK: test.txt==--" in wrapped
    assert content in wrapped
    assert "--==ATTACHMENT_BLOCK_END==--" in wrapped 

def test_pdf_converter(tmp_path):
    """Test PDF to markdown conversion."""
    # Create a test PDF file using PyMuPDF
    pdf_path = tmp_path / "test.pdf"
    doc = fitz.open()
    page = doc.new_page()
    
    # Add text
    page.insert_text((50, 50), "Test Heading", fontsize=16)
    page.insert_text((50, 100), "Test paragraph with some content.")
    
    # Add a table-like structure
    y = 150
    for i in range(3):
        x = 50
        for j in range(3):
            page.insert_text((x, y), f"Cell {i},{j}")
            x += 100
        y += 30
    
    # Save the test PDF
    doc.save(pdf_path)
    doc.close()
    
    # Test conversion
    converter = PDFConverter(temp_dir=tmp_path)
    content, metadata = converter.convert(pdf_path)
    
    # Check content
    assert "Test Heading" in content
    assert "Test paragraph" in content
    assert "Cell" in content
    
    # Check metadata
    assert metadata["original_format"] == "pdf"
    assert metadata["pages"] == 1
    assert "size" in metadata

def test_pdf_converter_with_images(tmp_path):
    """Test PDF to markdown conversion with images."""
    # Create a test PDF with an image
    pdf_path = tmp_path / "test_with_image.pdf"
    doc = fitz.open()
    page = doc.new_page()
    
    # Add text
    page.insert_text((50, 50), "PDF with Image")
    
    # Create and add a simple test image
    img_path = tmp_path / "test_image.png"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path)
    
    # Insert image into PDF
    rect = fitz.Rect(50, 100, 150, 200)
    page.insert_image(rect, filename=str(img_path))
    
    # Save the test PDF
    doc.save(pdf_path)
    doc.close()
    
    # Test conversion
    converter = PDFConverter(temp_dir=tmp_path)
    content, metadata = converter.convert(pdf_path)
    
    # Check content
    assert "PDF with Image" in content
    assert "### Images" in content
    
    # Check metadata
    assert metadata["original_format"] == "pdf"
    assert metadata["pages"] == 1
    assert "size" in metadata

def test_pdf_converter_complex_layout(tmp_path):
    """Test PDF to markdown conversion with complex layout."""
    # Create a test PDF with complex layout
    pdf_path = tmp_path / "test_complex.pdf"
    doc = fitz.open()
    page = doc.new_page()
    
    # Add various elements
    page.insert_text((50, 50), "Main Title", fontsize=20)
    page.insert_text((50, 100), "Section 1", fontsize=16)
    page.insert_text((50, 150), "Regular paragraph text with some content.")
    
    # Add bullet points
    y = 200
    for i in range(3):
        page.insert_text((70, y), f"• Bullet point {i+1}")
        y += 30
    
    # Add a table
    y = 300
    for i in range(3):
        x = 50
        for j in range(3):
            page.insert_text((x, y), f"Table {i},{j}")
            x += 100
        y += 30
    
    # Save the test PDF
    doc.save(pdf_path)
    doc.close()
    
    # Test conversion
    converter = PDFConverter(temp_dir=tmp_path)
    content, metadata = converter.convert(pdf_path)
    
    # Check content
    assert "Main Title" in content
    assert "Section 1" in content
    assert "Regular paragraph" in content
    assert "Bullet point" in content
    assert "Table" in content
    
    # Check metadata
    assert metadata["original_format"] == "pdf"
    assert metadata["pages"] == 1
    assert "size" in metadata

def test_image_converter_basic(tmp_path):
    """Test basic image conversion without AI description."""
    # Create a test image
    img_path = tmp_path / "test.png"
    img = Image.new('RGB', (100, 100), color='red')
    img.save(img_path)
    
    # Test conversion
    converter = ImageConverter()  # No API key provided
    content, metadata = converter.convert(img_path)
    
    # Check content
    assert f"![test.png]({img_path})" in content
    assert "**Description:** No AI description available" in content
    assert "**Technical Details:**" in content
    assert "Format: png" in content
    assert "Dimensions: 100x100" in content
    assert "Mode: RGB" in content
    
    # Check metadata
    assert metadata["original_format"] == "png"
    assert metadata["dimensions"] == "100x100"
    assert metadata["mode"] == "RGB"
    assert "size" in metadata
    assert "dpi" in metadata

def test_image_converter_heic(tmp_path):
    """Test HEIC image conversion."""
    # Create a test HEIC file (simulated as PNG for test)
    img_path = tmp_path / "test.heic"
    img = Image.new('RGB', (100, 100), color='blue')
    img.save(img_path, format='PNG')  # Save as PNG since HEIC might not be supported
    
    # Test conversion
    converter = ImageConverter()
    content, metadata = converter.convert(img_path)
    
    # Check content
    assert f"![test.heic]({img_path})" in content
    assert "**Description:** No AI description available" in content
    assert "**Technical Details:**" in content
    assert "Dimensions: 100x100" in content
    assert "Mode: RGB" in content
    
    # Check metadata
    assert metadata["dimensions"] == "100x100"
    assert metadata["mode"] == "RGB"
    assert "size" in metadata

def test_image_converter_with_vision_api(tmp_path, monkeypatch):
    """Test image conversion with OpenAI Vision API."""
    # Create a test image
    img_path = tmp_path / "test.jpg"
    img = Image.new('RGB', (100, 100), color='green')
    img.save(img_path)
    
    # Mock OpenAI API response
    class MockResponse:
        def __init__(self):
            self.choices = [type('Choice', (), {'message': type('Message', (), {'content': 'A solid green square image.'})()})]
    
    def mock_create(*args, **kwargs):
        return MockResponse()
    
    # Apply the mock
    import openai
    monkeypatch.setattr(openai.ChatCompletion, "create", mock_create)
    
    # Test conversion
    converter = ImageConverter(vision_api_key="test_key")
    content, metadata = converter.convert(img_path)
    
    # Check content
    assert f"![test.jpg]({img_path})" in content
    assert "**Description:** A solid green square image." in content
    assert "**Technical Details:**" in content
    assert "Format: jpeg" in content
    assert "Dimensions: 100x100" in content
    
    # Check metadata
    assert metadata["original_format"] == "jpeg"
    assert metadata["dimensions"] == "100x100"
    assert metadata["ai_description"] == "A solid green square image."

def test_image_converter_error_handling(tmp_path):
    """Test image converter error handling."""
    # Create an invalid image file
    img_path = tmp_path / "invalid.jpg"
    with open(img_path, 'w') as f:
        f.write("Not an image")
    
    # Test conversion
    converter = ImageConverter()
    with pytest.raises(ProcessingError, match="Image conversion failed"):
        converter.convert(img_path)

def test_content_validation_empty(converter_factory):
    """Test validation of empty content."""
    with pytest.raises(ProcessingError, match="Content cannot be empty"):
        converter_factory._validate_content("")

def test_content_validation_no_headers(converter_factory, caplog):
    """Test validation of content without headers."""
    content = "Some content without headers"
    converter_factory._validate_content(content)
    assert "Content has no headers" in caplog.text

def test_content_validation_broken_table(converter_factory):
    """Test validation of broken table structure."""
    # Table with inconsistent columns
    content = """
    | Header 1 | Header 2 |
    |----------|----------|
    | Cell 1 | Cell 2 | Extra Cell |
    """
    with pytest.raises(ProcessingError, match="Table has inconsistent number of columns"):
        converter_factory._validate_content(content)

def test_content_validation_unmatched_code_blocks(converter_factory):
    """Test validation of unmatched code blocks."""
    content = """
    ```python
    def test():
        pass
    """  # Missing closing code block
    with pytest.raises(ProcessingError, match="Unmatched code block markers"):
        converter_factory._validate_content(content)

def test_content_validation_image_alt_text(converter_factory, caplog):
    """Test validation of image alt text."""
    content = "![](image.jpg)"  # Missing alt text
    converter_factory._validate_content(content)
    assert "Image missing alt text" in caplog.text

def test_metadata_validation_missing_field(converter_factory):
    """Test validation of missing required metadata field."""
    metadata = {}  # Missing original_format
    with pytest.raises(ProcessingError, match="Missing required metadata field"):
        converter_factory._validate_metadata(metadata)

def test_metadata_validation_invalid_size(converter_factory):
    """Test validation of invalid size metadata."""
    metadata = {
        'original_format': 'test',
        'size': -1  # Invalid negative size
    }
    with pytest.raises(ProcessingError, match="File size must be positive"):
        converter_factory._validate_metadata(metadata)

def test_metadata_validation_invalid_dimensions(converter_factory):
    """Test validation of invalid dimensions metadata."""
    metadata = {
        'original_format': 'test',
        'dimensions': 'invalid'  # Invalid dimensions format
    }
    with pytest.raises(ProcessingError, match="Invalid dimensions format"):
        converter_factory._validate_metadata(metadata)

def test_metadata_validation_valid(converter_factory):
    """Test validation of valid metadata."""
    metadata = {
        'original_format': 'test',
        'size': 1000,
        'dimensions': '100x200'
    }
    # Should not raise any exceptions
    converter_factory._validate_metadata(metadata)

def test_detect_attachment_blocks(converter_factory):
    """Test detection of attachment blocks."""
    content = """
Some text before

--==ATTACHMENT_BLOCK: test1.txt==--
Content of first attachment
--==ATTACHMENT_BLOCK_END==--

Some text between

--==ATTACHMENT_BLOCK: test2.json==--
{
    "key": "value"
}
--==ATTACHMENT_BLOCK_END==--

Some text after
"""
    blocks = converter_factory.detect_attachment_blocks(content)
    
    assert len(blocks) == 2
    
    # Check first block
    assert blocks[0]['filename'] == 'test1.txt'
    assert blocks[0]['content'] == 'Content of first attachment'
    assert blocks[0]['start_line'] == 4
    assert blocks[0]['end_line'] == 6
    
    # Check second block
    assert blocks[1]['filename'] == 'test2.json'
    assert '"key": "value"' in blocks[1]['content']
    assert blocks[1]['start_line'] == 10
    assert blocks[1]['end_line'] == 14

def test_detect_unclosed_attachment_block(converter_factory, caplog):
    """Test detection of unclosed attachment block."""
    content = """
--==ATTACHMENT_BLOCK: test.txt==--
Content without end marker
Some more content
"""
    blocks = converter_factory.detect_attachment_blocks(content)
    
    assert len(blocks) == 0
    assert "Unclosed attachment block" in caplog.text

def test_extract_attachment_metadata(converter_factory):
    """Test extraction of attachment metadata."""
    block = {
        'filename': 'test.json',
        'content': '{"key": "value"}',
        'start_line': 1,
        'end_line': 3,
        'start_pos': 0,
        'end_pos': 50
    }
    
    metadata = converter_factory.extract_attachment_metadata(block)
    
    assert metadata['filename'] == 'test.json'
    assert metadata['file_type'] == 'json'
    assert metadata['line_range'] == (1, 3)
    assert metadata['byte_range'] == (0, 50)
    assert metadata['content_size'] > 0
    assert not metadata['has_references']

def test_extract_attachment_metadata_with_references(converter_factory):
    """Test extraction of attachment metadata with references."""
    block = {
        'filename': 'test.md',
        'content': 'Link to [[another file]]',
        'start_line': 1,
        'end_line': 3,
        'start_pos': 0,
        'end_pos': 50
    }
    
    metadata = converter_factory.extract_attachment_metadata(block)
    
    assert metadata['has_references']

def test_validate_attachment_block_missing_field(converter_factory):
    """Test validation of attachment block with missing field."""
    block = {
        'filename': 'test.txt',
        'content': 'Test content',
        # Missing start_line
        'end_line': 3,
        'start_pos': 0,
        'end_pos': 50
    }
    
    with pytest.raises(ProcessingError, match="Missing required field"):
        converter_factory.validate_attachment_block(block)

def test_validate_attachment_block_empty_filename(converter_factory):
    """Test validation of attachment block with empty filename."""
    block = {
        'filename': '',
        'content': 'Test content',
        'start_line': 1,
        'end_line': 3,
        'start_pos': 0,
        'end_pos': 50
    }
    
    with pytest.raises(ProcessingError, match="Empty filename"):
        converter_factory.validate_attachment_block(block)

def test_validate_attachment_block_invalid_range(converter_factory):
    """Test validation of attachment block with invalid range."""
    block = {
        'filename': 'test.txt',
        'content': 'Test content',
        'start_line': 3,  # Start after end
        'end_line': 1,
        'start_pos': 0,
        'end_pos': 50
    }
    
    with pytest.raises(ProcessingError, match="Invalid line range"):
        converter_factory.validate_attachment_block(block)

def test_validate_attachment_block_empty_content(converter_factory):
    """Test validation of attachment block with empty content."""
    block = {
        'filename': 'test.txt',
        'content': '',
        'start_line': 1,
        'end_line': 3,
        'start_pos': 0,
        'end_pos': 50
    }
    
    with pytest.raises(ProcessingError, match="Empty content"):
        converter_factory.validate_attachment_block(block)

def test_validate_attachment_block_valid(converter_factory):
    """Test validation of valid attachment block."""
    block = {
        'filename': 'test.txt',
        'content': 'Test content\nwith multiple lines',
        'start_line': 1,
        'end_line': 3,
        'start_pos': 0,
        'end_pos': 50
    }
    
    # Should not raise any exceptions
    converter_factory.validate_attachment_block(block)

def test_generate_anchor_id(converter_factory):
    """Test anchor ID generation."""
    # Basic case
    assert converter_factory.generate_anchor_id("Test Title") == "test-title"
    
    # Special characters
    assert converter_factory.generate_anchor_id("Test & Title!") == "test-title"
    
    # Multiple spaces
    assert converter_factory.generate_anchor_id("Test   Title") == "test-title"
    
    # Duplicate handling
    first = converter_factory.generate_anchor_id("test")
    second = converter_factory.generate_anchor_id("test")
    assert first == "test"
    assert second == "test-2"
    
    # Special characters and spaces
    assert converter_factory.generate_anchor_id("Test & Title!  With Spaces") == "test-title-with-spaces"

def test_add_anchor_ids(converter_factory):
    """Test adding anchor IDs to content."""
    content = """
# Section 1

Link to [[Test Reference]]

# Section 2

Another link to [[Test Reference]]
And a link to [[Another Reference]]
"""
    
    processed = converter_factory.add_anchor_ids(content)
    
    assert '<a id="test-reference"></a>[[Test Reference]]' in processed
    assert '<a id="another-reference"></a>[[Another Reference]]' in processed
    assert processed.count('<a id="test-reference"></a>') == 2

def test_update_cross_references(converter_factory):
    """Test updating cross-references."""
    # First add some anchor IDs
    converter_factory.generate_anchor_id("Test Reference")
    converter_factory.generate_anchor_id("Another Reference")
    
    content = """
# Section 1

Link to [[Test Reference]]

# Section 2

Another link to [[Test Reference]]
And a link to [[Another Reference]]
And a link to [[Missing Reference]]
"""
    
    processed = converter_factory.update_cross_references(content)
    
    assert '[Test Reference](#test-reference)' in processed
    assert '[Another Reference](#another-reference)' in processed
    assert '[Missing Reference](#missing-ref)' in processed

def test_get_anchor_id(converter_factory):
    """Test getting existing anchor IDs."""
    # Generate some IDs
    converter_factory.generate_anchor_id("Test")
    converter_factory.generate_anchor_id("Another Test")
    
    assert converter_factory.get_anchor_id("Test") == "test"
    assert converter_factory.get_anchor_id("Another Test") == "another-test"
    assert converter_factory.get_anchor_id("Non-existent") is None

def test_clear_anchor_ids(converter_factory):
    """Test clearing anchor IDs."""
    # Generate some IDs
    converter_factory.generate_anchor_id("Test")
    converter_factory.generate_anchor_id("Another Test")
    
    assert len(converter_factory._anchor_ids) == 2
    
    converter_factory.clear_anchor_ids()
    
    assert len(converter_factory._anchor_ids) == 0
    assert converter_factory.get_anchor_id("Test") is None

def test_anchor_id_duplicate_handling(converter_factory):
    """Test handling of duplicate anchor IDs."""
    # Generate multiple similar IDs
    id1 = converter_factory.generate_anchor_id("Test")
    id2 = converter_factory.generate_anchor_id("Test")
    id3 = converter_factory.generate_anchor_id("Test")
    
    assert id1 == "test"
    assert id2 == "test-1"
    assert id3 == "test-2"
    assert len(set([id1, id2, id3])) == 3  # All IDs should be unique

def test_anchor_id_special_characters(converter_factory):
    """Test anchor ID generation with special characters."""
    cases = [
        ("Test & Title!", "test-title"),
        ("Section 1.2.3", "section-123"),
        ("Special $#@% Characters", "special-characters"),
        ("Multiple   Spaces", "multiple-spaces"),
        ("Mixed-Case_Text", "mixed-case-text")
    ]
    
    for input_text, expected_id in cases:
        assert converter_factory.generate_anchor_id(input_text) == expected_id

def test_cross_reference_warning(converter_factory, caplog):
    """Test warning for missing cross-reference targets."""
    content = "Link to [[Non-existent Reference]]"
    
    converter_factory.update_cross_references(content)
    
    assert "Cross-reference target not found" in caplog.text

def test_resolve_relative_path_no_base(converter_factory):
    """Test resolving relative path without base path."""
    with pytest.raises(ProcessingError, match="No base path set"):
        converter_factory.resolve_relative_path("test.txt")

def test_resolve_relative_path_with_base(converter_factory, tmp_path):
    """Test resolving relative path with base path."""
    converter_factory.set_base_path(tmp_path)
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.touch()
    
    resolved = converter_factory.resolve_relative_path("test.txt")
    assert resolved == test_file.resolve()

def test_resolve_relative_path_with_reference(converter_factory, tmp_path):
    """Test resolving relative path with reference path."""
    # Create test directory structure
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    test_file = subdir / "test.txt"
    test_file.touch()
    
    reference_path = tmp_path / "reference.md"
    
    resolved = converter_factory.resolve_relative_path(
        "subdir/test.txt",
        reference_path=reference_path
    )
    assert resolved == test_file.resolve()

def test_resolve_absolute_path(converter_factory, tmp_path):
    """Test resolving absolute path."""
    # Test absolute file path
    abs_path = str(tmp_path / "test.txt")
    resolved = converter_factory.resolve_relative_path(abs_path)
    assert str(resolved) == abs_path
    
    # Test URLs
    url = "https://example.com/image.jpg"
    resolved = converter_factory.resolve_relative_path(url)
    assert str(resolved) == url

def test_update_relative_paths(converter_factory, tmp_path):
    """Test updating relative paths in content."""
    converter_factory.set_base_path(tmp_path)
    
    # Create test files
    (tmp_path / "image1.jpg").touch()
    (tmp_path / "image2.png").touch()
    
    content = """
# Test Document

![Image 1](image1.jpg)
Some text
![Image 2](image2.png)
"""
    
    processed = converter_factory.update_relative_paths(content)
    
    assert str(tmp_path / "image1.jpg") in processed
    assert str(tmp_path / "image2.png") in processed

def test_update_relative_paths_with_reference(converter_factory, tmp_path):
    """Test updating relative paths with reference path."""
    # Create test directory structure
    images = tmp_path / "images"
    images.mkdir()
    (images / "test.jpg").touch()
    
    content = "![Test](../images/test.jpg)"
    reference_path = tmp_path / "docs" / "doc.md"
    
    processed = converter_factory.update_relative_paths(content, reference_path)
    
    assert str(images / "test.jpg") in processed

def test_update_relative_paths_missing_file(converter_factory, tmp_path, caplog):
    """Test updating relative paths with missing file."""
    converter_factory.set_base_path(tmp_path)
    
    content = "![Missing](missing.jpg)"
    
    processed = converter_factory.update_relative_paths(content)
    
    assert "Failed to resolve path" in caplog.text
    assert content == processed  # Original content should be unchanged

def test_normalize_path(converter_factory, tmp_path):
    """Test path normalization."""
    converter_factory.set_base_path(tmp_path)
    
    # Create test file
    test_file = tmp_path / "test.txt"
    test_file.touch()
    
    # Test relative to base path
    normalized = converter_factory.normalize_path(test_file)
    assert normalized == "test.txt"
    
    # Test path outside base path
    outside_file = tmp_path.parent / "outside.txt"
    normalized = converter_factory.normalize_path(outside_file)
    assert str(outside_file) in normalized

def test_normalize_path_error(converter_factory, tmp_path, caplog):
    """Test path normalization error handling."""
    converter_factory.set_base_path(tmp_path)
    
    # Create invalid path
    invalid_path = Path("invalid/:/path")
    
    normalized = converter_factory.normalize_path(invalid_path)
    
    assert "Failed to normalize path" in caplog.text
    assert str(invalid_path) == normalized  # Should return original path string

def test_extract_navigation_links(converter_factory):
    """Test extraction of navigation links."""
    content = """
# Test Document

<!-- prev: prev.md -->
<!-- next: next.md -->
<!-- parent: parent.md -->

Some content
"""
    
    links = converter_factory.extract_navigation_links(content, "test.md")
    
    assert links['prev'] == 'prev.md'
    assert links['next'] == 'next.md'
    assert links['parent'] == 'parent.md'

def test_extract_navigation_links_partial(converter_factory):
    """Test extraction of partial navigation links."""
    content = """
# Test Document

<!-- prev: prev.md -->
<!-- parent: parent.md -->

Some content
"""
    
    links = converter_factory.extract_navigation_links(content, "test.md")
    
    assert links['prev'] == 'prev.md'
    assert links['parent'] == 'parent.md'
    assert 'next' not in links

def test_add_navigation_links(converter_factory, tmp_path):
    """Test adding navigation links."""
    converter_factory.set_base_path(tmp_path)
    
    # Create test files
    (tmp_path / "prev.md").touch()
    (tmp_path / "next.md").touch()
    (tmp_path / "parent.md").touch()
    
    # Set up navigation links
    file_path = str(tmp_path / "test.md")
    converter_factory._nav_links[file_path] = {
        'prev': 'prev.md',
        'next': 'next.md',
        'parent': 'parent.md'
    }
    
    content = "# Test Document\n\nSome content"
    
    processed = converter_factory.add_navigation_links(content, file_path)
    
    assert "## Navigation" in processed
    assert "← [Previous]" in processed
    assert "→ [Next]" in processed
    assert "↑ [Up]" in processed

def test_add_navigation_links_no_links(converter_factory):
    """Test adding navigation links when none exist."""
    content = "# Test Document\n\nSome content"
    
    processed = converter_factory.add_navigation_links(content, "test.md")
    
    assert processed == content  # Should be unchanged

def test_update_navigation_links(converter_factory, tmp_path):
    """Test updating navigation links."""
    converter_factory.set_base_path(tmp_path)
    
    # Create test files
    (tmp_path / "prev.md").touch()
    (tmp_path / "next.md").touch()
    
    content = """
# Test Document

<!-- prev: old_prev.md -->
<!-- next: old_next.md -->

Some content

---
## Navigation
← [Previous](#)
→ [Next](#)
"""
    
    file_path = str(tmp_path / "test.md")
    processed = converter_factory.update_navigation_links(content, file_path)
    
    # Old navigation should be removed
    assert "old_prev.md" not in processed
    assert "old_next.md" not in processed
    
    # New navigation should be added
    assert "## Navigation" in processed
    assert processed.count("## Navigation") == 1  # Only one navigation section

def test_validate_navigation_links(converter_factory, tmp_path):
    """Test validation of navigation links."""
    converter_factory.set_base_path(tmp_path)
    
    # Create test files
    (tmp_path / "file1.md").touch()
    (tmp_path / "file2.md").touch()
    (tmp_path / "parent.md").touch()
    
    # Set up valid navigation chain
    converter_factory._nav_links[str(tmp_path / "file1.md")] = {
        'next': 'file2.md',
        'parent': 'parent.md'
    }
    converter_factory._nav_links[str(tmp_path / "file2.md")] = {
        'prev': 'file1.md',
        'parent': 'parent.md'
    }
    converter_factory._nav_links[str(tmp_path / "parent.md")] = {}
    
    errors = converter_factory.validate_navigation_links()
    assert not errors  # Should be no errors

def test_validate_navigation_links_broken_chain(converter_factory, tmp_path):
    """Test validation of broken navigation chain."""
    converter_factory.set_base_path(tmp_path)
    
    # Create test files
    (tmp_path / "file1.md").touch()
    (tmp_path / "file2.md").touch()
    
    # Set up broken navigation chain
    converter_factory._nav_links[str(tmp_path / "file1.md")] = {
        'next': 'file2.md'
    }
    converter_factory._nav_links[str(tmp_path / "file2.md")] = {
        'prev': 'wrong.md'  # Wrong prev link
    }
    
    errors = converter_factory.validate_navigation_links()
    assert len(errors) == 1
    assert "Broken next/prev chain" in errors[0]

def test_validate_navigation_links_missing_parent(converter_factory, tmp_path):
    """Test validation of missing parent file."""
    converter_factory.set_base_path(tmp_path)
    
    # Create test file
    (tmp_path / "file1.md").touch()
    
    # Set up navigation with missing parent
    converter_factory._nav_links[str(tmp_path / "file1.md")] = {
        'parent': 'missing_parent.md'
    }
    
    errors = converter_factory.validate_navigation_links()
    assert len(errors) == 1
    assert "Parent file not found" in errors[0]

def test_clear_navigation_links(converter_factory):
    """Test clearing navigation links."""
    # Add some navigation links
    converter_factory._nav_links["file1.md"] = {'next': 'file2.md'}
    converter_factory._nav_links["file2.md"] = {'prev': 'file1.md'}
    
    assert len(converter_factory._nav_links) == 2
    
    converter_factory.clear_navigation_links()
    
    assert len(converter_factory._nav_links) == 0
  