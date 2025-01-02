"""Tests for metadata file path handling in subdirectories."""

import os
import pytest
from pathlib import Path
from nova.utils.path_utils import (
    get_metadata_path,
    get_markdown_path,
    get_safe_path,
    ensure_parent_dirs
)

@pytest.fixture
def test_dir(tmp_path):
    """Create a test directory structure."""
    # Create test directories
    base_dir = tmp_path / "test_docs"
    subdirs = [
        "subdir1",
        "subdir2/nested",
        "subdir3/deep/nested",
        "subdir4/with spaces/nested",
        "subdir5/with_special_chars!@#",
    ]
    
    # Create directories
    for subdir in subdirs:
        dir_path = base_dir / subdir
        dir_path.mkdir(parents=True, exist_ok=True)
        
    return base_dir

def test_metadata_in_root(test_dir):
    """Test metadata file generation in root directory."""
    test_file = test_dir / "test.txt"
    metadata_path = get_metadata_path(test_file)
    
    assert metadata_path.name == "test.metadata.json"
    assert metadata_path.parent == test_dir
    
def test_metadata_in_subdir(test_dir):
    """Test metadata file generation in subdirectory."""
    test_file = test_dir / "subdir1" / "test.txt"
    metadata_path = get_metadata_path(test_file)
    
    assert metadata_path.name == "test.metadata.json"
    assert metadata_path.parent == test_dir / "subdir1"
    
def test_metadata_in_nested_subdir(test_dir):
    """Test metadata file generation in nested subdirectory."""
    test_file = test_dir / "subdir2" / "nested" / "test.txt"
    metadata_path = get_metadata_path(test_file)
    
    assert metadata_path.name == "test.metadata.json"
    assert metadata_path.parent == test_dir / "subdir2" / "nested"
    
def test_metadata_in_deep_nested_subdir(test_dir):
    """Test metadata file generation in deeply nested subdirectory."""
    test_file = test_dir / "subdir3" / "deep" / "nested" / "test.txt"
    metadata_path = get_metadata_path(test_file)
    
    assert metadata_path.name == "test.metadata.json"
    assert metadata_path.parent == test_dir / "subdir3" / "deep" / "nested"
    
def test_metadata_with_spaces_in_path(test_dir):
    """Test metadata file generation with spaces in directory names."""
    test_file = test_dir / "subdir4" / "with spaces" / "nested" / "test.txt"
    metadata_path = get_metadata_path(test_file)
    
    assert metadata_path.name == "test.metadata.json"
    assert str(metadata_path.parent).replace(os.sep, '/') == str(test_dir / "subdir4/with_spaces/nested").replace(os.sep, '/')
    
def test_metadata_with_special_chars(test_dir):
    """Test metadata file generation with special characters in directory names."""
    # Create a directory with special characters
    special_dir = test_dir / "subdir5" / "with_special_chars!@#"
    special_dir.mkdir(parents=True, exist_ok=True)
    
    test_file = special_dir / "test.txt"
    metadata_path = get_metadata_path(test_file)
    
    assert metadata_path.name == "test.metadata.json"
    # The directory name should be sanitized with underscores replacing special chars
    expected_parent = test_dir / "subdir5" / "with_special_chars_"
    assert str(metadata_path.parent).replace(os.sep, '/') == str(expected_parent).replace(os.sep, '/')
    
def test_ensure_parent_dirs(test_dir):
    """Test parent directory creation for metadata files."""
    test_file = test_dir / "new_subdir" / "nested" / "test.txt"
    metadata_path = get_metadata_path(test_file)
    
    # Ensure parent directories exist
    ensure_parent_dirs(metadata_path)
    
    assert metadata_path.parent.exists()
    assert metadata_path.parent.is_dir()
    
def test_markdown_in_subdirs(test_dir):
    """Test markdown file generation in subdirectories."""
    test_file = test_dir / "subdir1" / "test.txt"
    markdown_path = get_markdown_path(test_file, "parse")
    
    assert markdown_path.name == "test.parse.md"
    assert markdown_path.parent == test_dir / "subdir1" 