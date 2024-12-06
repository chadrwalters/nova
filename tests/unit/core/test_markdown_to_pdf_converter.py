import pytest
from pathlib import Path
from src.core.markdown_to_pdf_converter import MarkdownToPDFConverter

def test_convert_markdown_to_pdf(sample_markdown_file, temp_output_dir):
    """Test converting a markdown file to PDF."""
    converter = MarkdownToPDFConverter()
    output_file = temp_output_dir / "output.pdf"
    
    converter.convert(sample_markdown_file, output_file)
    
    assert output_file.exists()
    assert output_file.stat().st_size > 0

def test_convert_with_custom_template(sample_markdown_file, test_data_dir, temp_output_dir):
    """Test converting markdown to PDF with a custom template."""
    # Create a custom template
    template_file = test_data_dir / "custom_template.html"
    template_content = """
    <!DOCTYPE html>
    <html>
    <head><title>{{ title }}</title></head>
    <body>{{ content }}</body>
    </html>
    """
    template_file.write_text(template_content)
    
    converter = MarkdownToPDFConverter(template_path=template_file)
    output_file = temp_output_dir / "output.pdf"
    
    converter.convert(sample_markdown_file, output_file)
    
    assert output_file.exists()
    assert output_file.stat().st_size > 0
    
    # Cleanup
    template_file.unlink()

def test_convert_with_custom_css(sample_markdown_file, test_data_dir, temp_output_dir):
    """Test converting markdown to PDF with custom CSS."""
    # Create a custom CSS file
    css_file = test_data_dir / "custom_style.css"
    css_content = """
    body { font-family: Arial, sans-serif; }
    h1 { color: blue; }
    """
    css_file.write_text(css_content)
    
    converter = MarkdownToPDFConverter(css_path=css_file)
    output_file = temp_output_dir / "output.pdf"
    
    converter.convert(sample_markdown_file, output_file)
    
    assert output_file.exists()
    assert output_file.stat().st_size > 0
    
    # Cleanup
    css_file.unlink()

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
    with pytest.raises(FileNotFoundError):
        converter = MarkdownToPDFConverter(template_path=Path("nonexistent.html"))
        converter.convert(sample_markdown_file, temp_output_dir / "output.pdf") 