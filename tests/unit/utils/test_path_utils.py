import pytest
from pathlib import Path
from src.utils.path_utils import ensure_dir_exists, get_relative_path, is_file_newer

def test_ensure_dir_exists(temp_output_dir):
    """Test directory creation."""
    test_dir = temp_output_dir / "test_dir" / "nested"
    ensure_dir_exists(test_dir)
    assert test_dir.exists()
    assert test_dir.is_dir()

def test_ensure_dir_exists_with_file(temp_output_dir):
    """Test ensuring directory exists when path points to a file."""
    test_file = temp_output_dir / "test.txt"
    test_file.touch()
    
    with pytest.raises(NotADirectoryError):
        ensure_dir_exists(test_file)

def test_get_relative_path(temp_output_dir):
    """Test getting relative path."""
    base_dir = temp_output_dir / "base"
    target_file = base_dir / "nested" / "file.txt"
    
    relative_path = get_relative_path(target_file, base_dir)
    assert str(relative_path) == "nested/file.txt"

def test_is_file_newer(temp_output_dir):
    """Test file timestamp comparison."""
    file1 = temp_output_dir / "file1.txt"
    file2 = temp_output_dir / "file2.txt"
    
    # Create files with different timestamps
    file1.touch()
    import time
    time.sleep(0.1)  # Ensure different timestamps
    file2.touch()
    
    assert is_file_newer(file2, file1)
    assert not is_file_newer(file1, file2)

def test_is_file_newer_nonexistent(temp_output_dir):
    """Test file timestamp comparison with non-existent file."""
    file1 = temp_output_dir / "file1.txt"
    file2 = temp_output_dir / "nonexistent.txt"
    
    file1.touch()
    
    with pytest.raises(FileNotFoundError):
        is_file_newer(file2, file1)
    
    with pytest.raises(FileNotFoundError):
        is_file_newer(file1, file2) 