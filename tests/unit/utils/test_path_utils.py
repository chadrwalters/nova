from pathlib import Path

import pytest

from src.utils.path_utils import ensure_dir_exists, get_relative_path, is_file_newer


def test_ensure_dir_exists(tmp_path: Path) -> None:
    """Test directory creation."""
    test_dir = tmp_path / "test_dir"
    ensure_dir_exists(test_dir)
    assert test_dir.exists()
    assert test_dir.is_dir()


def test_get_relative_path(tmp_path: Path) -> None:
    """Test relative path calculation."""
    base = tmp_path / "base"
    target = tmp_path / "base" / "sub" / "file.txt"
    rel_path = get_relative_path(target, base)
    assert str(rel_path) == "sub/file.txt"


def test_is_file_newer(tmp_path: Path) -> None:
    """Test file modification time comparison."""
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"

    # Create files with different timestamps
    file1.write_text("test1")
    import time

    time.sleep(0.1)  # Ensure different timestamps
    file2.write_text("test2")

    assert is_file_newer(file2, file1)
    assert not is_file_newer(file1, file2)
