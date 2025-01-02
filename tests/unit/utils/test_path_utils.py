"""Tests for path utilities."""

import os
from pathlib import Path
import pytest
from nova.utils.path_utils import (
    sanitize_filename,
    get_safe_path,
    get_metadata_path,
    get_markdown_path,
    get_relative_path
)

def test_sanitize_filename():
    """Test filename sanitization."""
    test_cases = [
        # Basic cases
        ("simple.txt", "simple.txt"),
        ("with spaces.txt", "with_spaces.txt"),
        ("multiple   spaces.txt", "multiple_spaces.txt"),
        
        # Special characters
        ("file<with>special:chars?.txt", "file_with_special_chars_.txt"),
        ("Time Off Tracker(Holiday Time Off Tracker)", "Time_Off_Tracker(Holiday_Time_Off_Tracker)"),
        ("06100-PO1-GTC for Audit & Certification Services_v6", "06100-PO1-GTC_for_Audit_&_Certification_Services_v6"),
        
        # Unicode characters
        ("résumé.pdf", "resume.pdf"),
        ("über.txt", "uber.txt"),
        ("документ.txt", "dokument.txt"),
        
        # Edge cases
        ("", "unnamed"),
        (".hidden", "hidden"),
        ("..multiple.dots..txt", "multiple.dots.txt"),
        (" leading trailing ", "leading_trailing"),
    ]
    
    for input_name, expected in test_cases:
        assert sanitize_filename(input_name) == expected

def test_get_safe_path(tmp_path):
    """Test safe path generation."""
    # Create test directory structure
    base_dir = tmp_path / "test_dir"
    base_dir.mkdir()
    
    test_cases = [
        # Basic paths
        ("simple.txt", "simple.txt"),
        ("dir/file.txt", "dir/file.txt"),
        
        # Paths with special characters
        ("dir with spaces/file.txt", "dir_with_spaces/file.txt"),
        ("Time Off Tracker(Holiday Time Off Tracker)/doc.txt",
         "Time_Off_Tracker(Holiday_Time_Off_Tracker)/doc.txt"),
         
        # Deep paths
        ("a/b/c/d/file.txt", "a/b/c/d/file.txt"),
        ("a/b/../c/file.txt", "a/c/file.txt"),  # Path normalization
    ]
    
    for input_path, expected in test_cases:
        full_path = base_dir / input_path
        safe_path = get_safe_path(full_path, make_relative_to=base_dir)
        assert str(safe_path).replace(os.sep, '/') == expected

def test_get_metadata_path(tmp_path):
    """Test metadata path generation."""
    test_cases = [
        # Basic cases
        ("doc.txt", "doc.metadata.json"),
        ("dir/doc.txt", "dir/doc.metadata.json"),
        
        # Special characters
        ("Time Off Tracker/doc.txt", "Time_Off_Tracker/doc.metadata.json"),
        ("dir with spaces/doc.txt", "dir_with_spaces/doc.metadata.json"),
    ]
    
    for input_path, expected in test_cases:
        path = tmp_path / input_path
        metadata_path = get_metadata_path(path)
        assert str(metadata_path.relative_to(tmp_path)).replace(os.sep, '/') == expected

def test_get_markdown_path(tmp_path):
    """Test markdown path generation."""
    test_cases = [
        # Basic cases
        (("doc.txt", "parse"), "doc.parse.md"),
        (("dir/doc.txt", "split"), "dir/doc.split.md"),
        
        # Special characters
        (("Time Off Tracker/doc.txt", "parse"), "Time_Off_Tracker/doc.parse.md"),
        (("dir with spaces/doc.txt", "final"), "dir_with_spaces/doc.final.md"),
    ]
    
    for (input_path, phase), expected in test_cases:
        path = tmp_path / input_path
        md_path = get_markdown_path(path, phase)
        assert str(md_path.relative_to(tmp_path)).replace(os.sep, '/') == expected

def test_get_relative_path(tmp_path):
    """Test relative path generation."""
    # Create test directory structure
    base_dir = tmp_path / "test_dir"
    base_dir.mkdir()
    
    test_cases = [
        # Same directory
        (("a.txt", "b.txt"), "b.txt"),
        
        # Subdirectory
        (("dir1/a.txt", "dir2/b.txt"), "../dir2/b.txt"),
        
        # Deep paths
        (("a/b/c/d.txt", "a/b/e/f.txt"), "../../e/f.txt"),
        
        # Special characters
        (("Time Off Tracker/a.txt", "dir/b.txt"), "../dir/b.txt"),
        (("dir with spaces/a.txt", "other dir/b.txt"), "../other_dir/b.txt"),
    ]
    
    for (from_path, to_path), expected in test_cases:
        from_full = base_dir / from_path
        to_full = base_dir / to_path
        rel_path = get_relative_path(from_full, to_full)
        assert rel_path == expected 