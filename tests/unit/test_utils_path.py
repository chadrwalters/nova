"""Unit tests for Nova path utilities."""
import pytest
from pathlib import Path

from nova.utils.path_utils import (
    sanitize_filename,
    get_relative_path,
    get_safe_path,
    get_metadata_path,
    get_markdown_path
)

class TestSanitizeFilename:
    """Tests for filename sanitization."""
    
    def test_remove_invalid_chars(self):
        """Test removal of invalid characters from filenames."""
        test_cases = [
            # Basic invalid characters
            ('file<>:"/\\|?*name.txt', 'file_name_.txt'),
            ('file!@#$%^{}.txt', 'file_.txt'),
            ('file\x00\x1f.txt', 'file_.txt'),
            
            # Multiple spaces and underscores
            ('file   name.txt', 'file_name.txt'),
            ('file___name.txt', 'file_name.txt'),
            ('file _ name.txt', 'file_name.txt'),
            
            # Leading/trailing dots and spaces
            (' file.txt', 'file.txt'),
            ('..file.txt..', 'file.txt. '),
            (' . file.txt . ', 'file.txt. '),
            
            # Empty or all invalid
            ('', 'unnamed'),
            ('???', 'unnamed_'),
            ('.....', 'unnamed'),
            
            # Preserve valid characters
            ('file-name(1).txt', 'file-name(1).txt'),
            ('test_file-123.pdf', 'test_file-123.pdf'),
            ('document&notes.md', 'document&notes.md')
        ]
        
        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert result == expected, f"Failed for input '{input_name}': expected '{expected}' but got '{result}'"
    
    def test_cyrillic_to_latin(self):
        """Test conversion of Cyrillic characters to Latin."""
        test_cases = [
            # Basic Cyrillic
            ('файл.txt', 'fail.txt'),
            ('документ.pdf', 'dokument.pdf'),
            ('тест.md', 'test.md'),
            
            # Mixed Cyrillic and Latin
            ('file-тест.txt', 'file-test.txt'),
            ('тест-file.pdf', 'test-file.pdf'),
            ('doc_файл.md', 'doc_fail.md'),
            
            # Case preservation
            ('Файл.txt', 'Fail.txt'),
            ('ТЕСТ.pdf', 'TEST.pdf'),
            ('ТестФайл.md', 'TestFail.md'),
            
            # Special characters
            ('тест-файл.txt', 'test-fail.txt'),
            ('тест_файл.pdf', 'test_fail.pdf'),
            ('тест(1).md', 'test(1).md')
        ]
        
        for input_name, expected in test_cases:
            assert sanitize_filename(input_name) == expected

class TestRelativePath:
    """Tests for relative path calculations."""
    
    def test_same_directory(self, tmp_path: Path):
        """Test relative path calculation for files in same directory."""
        # Create test files
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.touch()
        file2.touch()
        
        # Test relative paths
        assert get_relative_path(file1, file2) == "file2.txt"
        assert get_relative_path(file2, file1) == "file1.txt"
    
    def test_different_directory(self, tmp_path: Path):
        """Test relative path calculation for files in different directories."""
        # Create directory structure
        dir1 = tmp_path / "dir1"
        dir2 = tmp_path / "dir2"
        dir1.mkdir()
        dir2.mkdir()
        
        # Create test files
        file1 = dir1 / "file1.txt"
        file2 = dir2 / "file2.txt"
        file1.touch()
        file2.touch()
        
        # Test relative paths
        assert get_relative_path(file1, file2) == "../dir2/file2.txt"
        assert get_relative_path(file2, file1) == "../dir1/file1.txt"

    def test_nested_directories(self, tmp_path: Path):
        """Test relative path calculation for nested directories."""
        # Create nested directory structure
        dir1 = tmp_path / "dir1"
        dir2 = dir1 / "dir2"
        dir3 = dir2 / "dir3"
        dir1.mkdir()
        dir2.mkdir()
        dir3.mkdir()
        
        # Create test files
        file1 = dir1 / "file1.txt"
        file2 = dir3 / "file2.txt"
        file1.touch()
        file2.touch()
        
        # Test relative paths
        assert get_relative_path(file1, file2) == "dir2/dir3/file2.txt"
        assert get_relative_path(file2, file1) == "../../file1.txt"

class TestPathNormalization:
    """Tests for path normalization."""
    
    def test_normalize_separators(self):
        """Test normalization of path separators."""
        test_cases = [
            ("file.txt", "file.txt"),
            ("dir1\\file.txt", "file.txt"),
            ("dir1/file.txt", "file.txt"),
            ("dir1//file.txt", "file.txt"),
            ("dir1\\\\file.txt", "file.txt")
        ]
        
        for input_path, expected in test_cases:
            path = Path(input_path)
            normalized = get_safe_path(path)
            assert normalized.name == expected
    
    def test_resolve_dots(self, tmp_path: Path):
        """Test resolution of . and .. in paths."""
        # Create directory structure
        dir1 = tmp_path / "dir1"
        dir1.mkdir()
        
        test_cases = [
            ("dir1/./file.txt", str(tmp_path / "dir1/file.txt")),
            ("dir1/../file.txt", str(tmp_path / "file.txt")),
            ("./dir1/../file.txt", str(tmp_path / "file.txt")),
            ("dir1/foo/../file.txt", str(tmp_path / "dir1/file.txt"))
        ]
        
        for input_path, expected in test_cases:
            path = tmp_path / input_path
            normalized = get_safe_path(path)
            assert str(normalized) == expected

class TestMetadataPath:
    """Tests for metadata path generation."""
    
    def test_metadata_path_generation(self, tmp_path: Path):
        """Test generation of metadata file paths."""
        test_cases = [
            ("doc.txt", "doc.metadata.json"),
            ("doc", "doc.metadata.json"),
            ("path.with.dots.txt", "path.with.metadata.json"),
            (".hidden", ".metadata.json")
        ]
        
        for input_path, expected in test_cases:
            path = tmp_path / input_path
            metadata_path = get_metadata_path(path)
            assert metadata_path.name == expected

class TestMarkdownPath:
    """Tests for markdown path generation."""
    
    def test_markdown_path_generation(self, tmp_path: Path):
        """Test generation of markdown file paths."""
        test_cases = [
            ("file.txt", "parse", "file.parse.md"),
            ("doc", "final", "doc.final.md"),
            ("path.with.dots.txt", "parse", "path.with.dots.parse.md"),
            (".hidden", "split", ".hidden.split.md")
        ]
        
        for input_path, phase, expected in test_cases:
            path = tmp_path / input_path
            markdown_path = get_markdown_path(path, phase)
            assert markdown_path.name == expected 