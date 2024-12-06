import pytest
from pathlib import Path
from src.core.markdown_consolidator import MarkdownConsolidator

def test_consolidate_single_file(sample_markdown_file, temp_output_dir):
    """Test consolidating a single markdown file."""
    consolidator = MarkdownConsolidator()
    output_file = temp_output_dir / "output.md"
    
    consolidator.consolidate([sample_markdown_file], output_file)
    
    assert output_file.exists()
    content = output_file.read_text()
    assert "# Test Document" in content
    assert "## Section 1" in content
    assert "## Section 2" in content

def test_consolidate_with_images(sample_markdown_file, sample_image_file, temp_output_dir):
    """Test consolidating markdown with image references."""
    # Modify the sample file to include an image reference
    content = sample_markdown_file.read_text()
    content += f"\n\n![Test Image]({sample_image_file.name})"
    sample_markdown_file.write_text(content)
    
    consolidator = MarkdownConsolidator()
    output_file = temp_output_dir / "output.md"
    
    consolidator.consolidate([sample_markdown_file], output_file)
    
    assert output_file.exists()
    output_content = output_file.read_text()
    assert "![Test Image]" in output_content
    assert sample_image_file.name in output_content

def test_consolidate_multiple_files(test_data_dir, temp_output_dir):
    """Test consolidating multiple markdown files."""
    # Create multiple test files
    file1 = test_data_dir / "file1.md"
    file2 = test_data_dir / "file2.md"
    
    file1.write_text("# File 1\nContent 1")
    file2.write_text("# File 2\nContent 2")
    
    consolidator = MarkdownConsolidator()
    output_file = temp_output_dir / "output.md"
    
    consolidator.consolidate([file1, file2], output_file)
    
    assert output_file.exists()
    content = output_file.read_text()
    assert "# File 1" in content
    assert "# File 2" in content
    assert "Content 1" in content
    assert "Content 2" in content
    
    # Cleanup
    file1.unlink()
    file2.unlink()

def test_empty_input_list():
    """Test consolidating an empty list of files."""
    consolidator = MarkdownConsolidator()
    with pytest.raises(ValueError):
        consolidator.consolidate([], Path("output.md"))

def test_invalid_input_file(temp_output_dir):
    """Test consolidating a non-existent file."""
    consolidator = MarkdownConsolidator()
    with pytest.raises(FileNotFoundError):
        consolidator.consolidate([Path("nonexistent.md")], temp_output_dir / "output.md") 