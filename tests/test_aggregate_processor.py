#!/usr/bin/env python3

import os
import pytest
from pathlib import Path
from aggregate_processor import AggregateProcessor

@pytest.fixture
def setup_dirs(tmp_path):
    """Set up test directories."""
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    
    input_dir.mkdir()
    output_dir.mkdir()
    
    return input_dir, output_dir

@pytest.fixture
def create_test_files(setup_dirs):
    """Create test markdown files."""
    input_dir, _ = setup_dirs
    
    # Create test files
    file1 = input_dir / "test1.md"
    file1.write_text("""# Test Document 1

This is the first test document.
""")
    
    file2 = input_dir / "test2.md"
    file2.write_text("""# Test Document 2

This is the second test document.
""")
    
    # Create nested directory
    nested_dir = input_dir / "nested"
    nested_dir.mkdir()
    
    file3 = nested_dir / "test3.md"
    file3.write_text("""# Test Document 3

This is a nested test document.
""")
    
    return [file1, file2, file3]

def test_processor_initialization(setup_dirs):
    """Test aggregate processor initialization."""
    input_dir, output_dir = setup_dirs
    processor = AggregateProcessor(input_dir, output_dir)
    
    assert processor.input_dir == input_dir
    assert processor.output_dir == output_dir

def test_file_aggregation(setup_dirs, create_test_files):
    """Test aggregating multiple markdown files."""
    input_dir, output_dir = setup_dirs
    test_files = create_test_files
    
    processor = AggregateProcessor(input_dir, output_dir)
    result = processor.process()
    
    assert result is not None
    assert result['output_file'] == str(output_dir / "all_merged_markdown.md")
    assert len(result['processed_files']) == 3
    
    # Check output file
    output_file = Path(result['output_file'])
    assert output_file.exists()
    
    # Check content
    content = output_file.read_text()
    assert "# Aggregated Markdown Files" in content
    assert "Generated on:" in content
    assert "File: test1.md" in content
    assert "File: test2.md" in content
    assert "File: nested/test3.md" in content
    assert "# Test Document 1" in content
    assert "# Test Document 2" in content
    assert "# Test Document 3" in content
    assert "# File Index" in content

def test_empty_directory(setup_dirs):
    """Test handling empty input directory."""
    input_dir, output_dir = setup_dirs
    
    processor = AggregateProcessor(input_dir, output_dir)
    result = processor.process()
    
    assert result is None

def test_invalid_file_handling(setup_dirs):
    """Test handling invalid files."""
    input_dir, output_dir = setup_dirs
    
    # Create invalid file
    invalid_file = input_dir / "invalid.md"
    invalid_file.write_bytes(b"\x80\x81")  # Invalid UTF-8
    
    # Create valid file
    valid_file = input_dir / "valid.md"
    valid_file.write_text("# Valid File")
    
    processor = AggregateProcessor(input_dir, output_dir)
    result = processor.process()
    
    assert result is not None
    assert len(result['processed_files']) == 1  # Only the valid file
    
    # Check content
    output_file = Path(result['output_file'])
    content = output_file.read_text()
    assert "# Valid File" in content

def test_file_order(setup_dirs):
    """Test that files are processed in sorted order."""
    input_dir, output_dir = setup_dirs
    
    # Create files in non-alphabetical order
    file_c = input_dir / "c.md"
    file_a = input_dir / "a.md"
    file_b = input_dir / "b.md"
    
    file_c.write_text("# C")
    file_a.write_text("# A")
    file_b.write_text("# B")
    
    processor = AggregateProcessor(input_dir, output_dir)
    result = processor.process()
    
    assert result is not None
    processed_paths = [Path(f['relative_path']).name for f in result['processed_files']]
    assert processed_paths == ['a.md', 'b.md', 'c.md']

def test_nested_directory_structure(setup_dirs):
    """Test handling nested directory structure."""
    input_dir, output_dir = setup_dirs
    
    # Create nested directory structure
    dir1 = input_dir / "dir1"
    dir2 = dir1 / "dir2"
    dir2.mkdir(parents=True)
    
    # Create files at different levels
    file1 = input_dir / "root.md"
    file2 = dir1 / "level1.md"
    file3 = dir2 / "level2.md"
    
    file1.write_text("# Root")
    file2.write_text("# Level 1")
    file3.write_text("# Level 2")
    
    processor = AggregateProcessor(input_dir, output_dir)
    result = processor.process()
    
    assert result is not None
    assert len(result['processed_files']) == 3
    
    # Check that relative paths are preserved
    paths = {Path(f['relative_path']) for f in result['processed_files']}
    assert Path('root.md') in paths
    assert Path('dir1/level1.md') in paths
    assert Path('dir1/dir2/level2.md') in paths

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 