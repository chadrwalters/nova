"""Unit tests for the MarkdownWriter class."""

import pytest
from pathlib import Path
from nova.core.markdown import MarkdownWriter


def test_write_section():
    """Test section writing with different heading levels."""
    writer = MarkdownWriter(base_level=1)
    
    # Test basic section
    result = writer.write_section("Test", "Content")
    assert result == "# Test\n\nContent\n"
    
    # Test nested section
    result = writer.write_section("Nested", "Nested Content", level=2)
    assert result == "## Nested\n\nNested Content\n"
    
    # Test with different base level
    writer = MarkdownWriter(base_level=2)
    result = writer.write_section("Test", "Content")
    assert result == "## Test\n\nContent\n"


def test_write_metadata():
    """Test metadata writing in YAML front matter format."""
    writer = MarkdownWriter()
    
    # Test empty metadata
    assert writer.write_metadata({}) == ""
    
    # Test basic metadata
    metadata = {
        "title": "Test Document",
        "author": "Test Author",
        "date": "2024-03-20"
    }
    result = writer.write_metadata(metadata)
    expected = "---\ntitle: Test Document\nauthor: Test Author\ndate: 2024-03-20\n---\n"
    assert result == expected


def test_write_reference():
    """Test reference link writing."""
    writer = MarkdownWriter()
    
    # Test attachment reference
    result = writer.write_reference("ATTACH", "document.pdf", "Document")
    assert result == "[Document][ATTACH:document.pdf]"
    
    # Test link reference
    result = writer.write_reference("LINK", "https://example.com", "Example")
    assert result == "[Example][LINK:https://example.com]"


def test_write_image_reference():
    """Test image reference writing."""
    writer = MarkdownWriter()
    
    # Test basic image reference
    result = writer.write_image_reference("image.jpg", "Alt Text")
    assert result == "![Alt Text](image.jpg)"
    
    # Test image reference with title
    result = writer.write_image_reference("image.jpg", "Alt Text", "Title")
    assert result == '![Alt Text](image.jpg "Title")'


def test_write_from_template(tmp_path):
    """Test template-based content generation."""
    # Create a test template
    template_dir = tmp_path / "templates"
    template_dir.mkdir()
    test_template = template_dir / "test.md"
    test_template.write_text("# {title}\n\n{content}\n\n[{link_text}]({link_url})")
    
    # Create writer with custom template dir
    writer = MarkdownWriter(template_dir=template_dir)
    
    # Test template rendering
    result = writer.write_from_template(
        "test",
        title="Test Title",
        content="Test Content",
        link_text="Link",
        link_url="https://example.com"
    )
    expected = "# Test Title\n\nTest Content\n\n[Link](https://example.com)"
    assert result == expected
    
    # Test missing template
    with pytest.raises(FileNotFoundError):
        writer.write_from_template("nonexistent")
    
    # Test missing variable
    with pytest.raises(KeyError):
        writer.write_from_template("test", title="Test")


def test_write_document(tmp_path):
    """Test document writing with base template."""
    writer = MarkdownWriter()  # Uses default template dir
    
    # Test document writing
    file_path = Path("/test/document.pdf")
    output_path = Path("/test/output/document.md")
    metadata = {"title": "Test", "author": "Author"}
    
    result = writer.write_document(
        title="Test Document",
        content="Test Content",
        metadata=metadata,
        file_path=file_path,
        output_path=output_path
    )
    
    # Verify basic structure (exact path handling depends on OS)
    assert "# Test Document" in result
    assert "Test Content" in result
    assert "title: Test" in result
    assert "author: Author" in result
    assert "document.pdf" in result


def test_write_image(tmp_path):
    """Test image document writing with image template."""
    writer = MarkdownWriter()  # Uses default template dir
    
    # Test image writing
    file_path = Path("/test/image.jpg")
    image_path = Path("/test/processed/image.jpg")
    output_path = Path("/test/output/image.md")
    metadata = {"title": "Test Image", "date": "2024-03-20"}
    
    result = writer.write_image(
        title="Test Image",
        image_path=image_path,
        alt_text="Test Alt Text",
        description="Test Description",
        analysis="Test Analysis",
        metadata=metadata,
        file_path=file_path,
        output_path=output_path
    )
    
    # Verify basic structure (exact path handling depends on OS)
    assert "# Test Image" in result
    assert "Test Alt Text" in result
    assert "Test Description" in result
    assert "Test Analysis" in result
    assert "title: Test Image" in result
    assert "date: 2024-03-20" in result
    assert "image.jpg" in result 