from pathlib import Path

import pytest

from src.core.markdown_to_pdf_converter import (
    MarkdownToPDFConverter,
    convert_markdown_to_pdf,
)


def test_convert_markdown_to_pdf(sample_markdown_file, temp_output_dir):
    """Test converting a markdown file to PDF."""
    converter = MarkdownToPDFConverter()
    output_file = temp_output_dir / "output.pdf"

    converter.convert(sample_markdown_file, output_file)

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_convert_with_custom_template(
    sample_markdown_file, test_data_dir, temp_output_dir
):
    """Test converting markdown to PDF with a custom template."""
    # Create a custom template
    template_dir = test_data_dir
    template_file = template_dir / "default_template.html"
    template_content = """
    <!DOCTYPE html>
    <html>
    <head><title>{{ title }}</title></head>
    <body>{{ content|safe }}</body>
    </html>
    """
    template_file.write_text(template_content)

    # Create converter with template directory
    converter = MarkdownToPDFConverter(template_dir=template_dir)
    output_file = temp_output_dir / "output.pdf"

    # Convert markdown to PDF
    converter.convert(sample_markdown_file, output_file)

    # Verify results
    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Cleanup
    template_file.unlink()


def test_convert_with_custom_css(sample_markdown_file, test_data_dir, temp_output_dir):
    """Test converting markdown to PDF with custom CSS."""
    # Create test directories
    template_dir = test_data_dir / "templates"
    style_dir = test_data_dir / "styles"
    template_dir.mkdir(exist_ok=True)
    style_dir.mkdir(exist_ok=True)

    # Create a custom template
    template_file = template_dir / "default_template.html"
    template_content = """
    <!DOCTYPE html>
    <html>
    <head><title>{{ title }}</title></head>
    <body>{{ content|safe }}</body>
    </html>
    """
    template_file.write_text(template_content)

    # Create a custom CSS file
    css_file = style_dir / "default_style.css"
    css_content = """
    body { font-family: Arial, sans-serif; }
    h1 { color: blue; }
    """
    css_file.write_text(css_content)

    # Create converter with template directory
    converter = MarkdownToPDFConverter(template_dir=template_dir)
    output_file = temp_output_dir / "output.pdf"

    # Convert markdown to PDF
    converter.convert(sample_markdown_file, output_file)

    # Verify results
    assert output_file.exists()
    assert output_file.stat().st_size > 0

    # Cleanup
    template_file.unlink()
    css_file.unlink()
    template_dir.rmdir()
    style_dir.rmdir()


def test_convert_with_images(sample_markdown_file, sample_image_file, temp_output_dir):
    """Test converting markdown with images to PDF."""
    # Modify the sample file to include an image reference
    content = sample_markdown_file.read_text()
    content += f"\n\n![Test Image]({sample_image_file})"
    sample_markdown_file.write_text(content)

    converter = MarkdownToPDFConverter()
    output_file = temp_output_dir / "output.pdf"

    converter.convert(sample_markdown_file, output_file)

    assert output_file.exists()
    assert output_file.stat().st_size > 0


def test_invalid_input_file(temp_output_dir):
    """Test converting a non-existent markdown file."""
    converter = MarkdownToPDFConverter()
    with pytest.raises(FileNotFoundError):
        converter.convert(Path("nonexistent.md"), temp_output_dir / "output.pdf")


def test_invalid_template_path(sample_markdown_file, temp_output_dir):
    """Test converting with a non-existent template."""
    # Create converter with invalid template directory
    template_dir = Path("nonexistent_templates")
    converter = MarkdownToPDFConverter(template_dir=template_dir)
    output_file = temp_output_dir / "output.pdf"

    # Attempt conversion
    with pytest.raises(FileNotFoundError):
        converter.convert(sample_markdown_file, output_file)


def create_converter_with_template(template_dir: Path) -> MarkdownToPDFConverter:
    """Create a converter with the specified template directory."""
    return MarkdownToPDFConverter(template_dir=template_dir)


@pytest.fixture
def invalid_template_converter(tmp_path: Path) -> MarkdownToPDFConverter:
    """Create a converter with an invalid template directory."""
    template_dir = tmp_path / "nonexistent_templates"
    return MarkdownToPDFConverter(template_dir=template_dir)


def test_convert_markdown_to_pdf_invalid_input(tmp_path: Path) -> None:
    """Test converting markdown to PDF with invalid input."""
    input_file = tmp_path / "nonexistent.md"
    output_file = tmp_path / "output.pdf"

    with pytest.raises(FileNotFoundError):
        convert_markdown_to_pdf(input_file, output_file)


def test_convert_markdown_to_pdf_invalid_template(
    tmp_path: Path,
    sample_markdown_file: Path,
) -> None:
    """Test converting markdown to PDF with invalid template."""
    # Prepare test data
    output_file = tmp_path / "output.pdf"
    nonexistent_dir = tmp_path / "nonexistent_templates"
    converter = MarkdownToPDFConverter(template_dir=nonexistent_dir)

    # Test conversion with invalid template directory
    with pytest.raises(FileNotFoundError):
        converter.convert(sample_markdown_file, output_file)
