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
            ('file<>:"/\\|?*name.txt', 'file_name.txt'),
            ('file!@#$%^{}.txt', 'file_.txt'),
            ('file\x00\x1f.txt', 'file_.txt'),
            
            # Multiple spaces and underscores
            ('file   name.txt', 'file_name.txt'),
            ('file___name.txt', 'file_name.txt'),
            ('file _ name.txt', 'file_name.txt'),
            
            # Leading/trailing dots and spaces
            (' file.txt ', 'file.txt'),
            ('..file.txt..', 'file.txt'),
            (' . file.txt . ', 'file.txt'),
            
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
            assert sanitize_filename(input_name) == expected
    
    def test_cyrillic_to_latin(self):
        """Test conversion of Cyrillic characters to Latin."""
        test_cases = [
            # Basic Cyrillic
            ('файл.txt', 'fayl.txt'),
            ('документ.pdf', 'dokument.pdf'),
            ('тест.md', 'test.md'),
            
            # Mixed Cyrillic and Latin
            ('file-тест.txt', 'file-test.txt'),
            ('тест-file.pdf', 'test-file.pdf'),
            ('doc_файл.md', 'doc_fayl.md'),
            
            # Case preservation
            ('Файл.txt', 'Fayl.txt'),
            ('ТЕСТ.pdf', 'TEST.pdf'),
            ('ТестФайл.md', 'TestFayl.md'),
            
            # Special characters
            ('тест-файл.txt', 'test-fayl.txt'),
            ('тест_файл.pdf', 'test_fayl.pdf'),
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
        dir1 = tmp_path / "a" / "b" / "c"
        dir2 = tmp_path / "a" / "d" / "e"
        dir1.mkdir(parents=True)
        dir2.mkdir(parents=True)
        
        # Create test files
        file1 = dir1 / "file1.txt"
        file2 = dir2 / "file2.txt"
        file1.touch()
        file2.touch()
        
        # Test relative paths
        assert get_relative_path(file1, file2) == "../../d/e/file2.txt"
        assert get_relative_path(file2, file1) == "../../b/c/file1.txt"

class TestPathNormalization:
    """Tests for path normalization."""
    
    def test_normalize_separators(self, tmp_path: Path):
        """Test normalization of path separators."""
        # Create test paths with different separators
        paths = [
            (tmp_path / "dir1/file.txt", "dir1/file.txt"),
            (tmp_path / "dir1\\file.txt", "dir1/file.txt"),
            (tmp_path / "dir1" / "dir2/file.txt", "dir1/dir2/file.txt"),
            (tmp_path / "dir1" / "dir2\\file.txt", "dir1/dir2/file.txt")
        ]
        
        for path, expected in paths:
            normalized = str(get_safe_path(path)).replace(str(tmp_path), "").lstrip("/\\")
            assert normalized == expected
    
    def test_resolve_dots(self, tmp_path: Path):
        """Test resolution of . and .. in paths."""
        # Create test paths with dots
        paths = [
            (tmp_path / "dir1/./file.txt", "dir1/file.txt"),
            (tmp_path / "dir1/../file.txt", "file.txt"),
            (tmp_path / "dir1/dir2/../file.txt", "dir1/file.txt"),
            (tmp_path / "dir1/./dir2/./../file.txt", "dir1/file.txt")
        ]
        
        for path, expected in paths:
            normalized = str(get_safe_path(path)).replace(str(tmp_path), "").lstrip("/\\")
            assert normalized == expected

class TestMetadataPath:
    """Tests for metadata path generation."""
    
    def test_metadata_path_generation(self, tmp_path: Path):
        """Test generation of metadata file paths."""
        test_cases = [
            # Basic files
            ("file.txt", "file.metadata.json"),
            ("document.pdf", "document.metadata.json"),
            ("notes.md", "notes.metadata.json"),
            
            # Files with multiple extensions
            ("file.parsed.md", "file.metadata.json"),
            ("doc.final.pdf", "doc.final.metadata.json"),
            
            # Files with special characters
            ("test-file.txt", "test-file.metadata.json"),
            ("test_file.pdf", "test_file.metadata.json"),
            ("test file.md", "test_file.metadata.json")
        ]
        
        for input_name, expected in test_cases:
            file_path = tmp_path / input_name
            metadata_path = get_metadata_path(file_path)
            assert metadata_path.name == expected
            assert metadata_path.parent == file_path.parent

class TestMarkdownPath:
    """Tests for markdown path generation."""
    
    def test_markdown_path_generation(self, tmp_path: Path):
        """Test generation of markdown file paths."""
        test_cases = [
            # Basic files
            ("file.txt", "parse", "file.parse.md"),
            ("document.pdf", "split", "document.split.md"),
            ("notes.md", "finalize", "notes.finalize.md"),
            
            # Files with multiple extensions
            ("file.parsed.md", "parse", "file.parse.md"),
            ("doc.final.pdf", "split", "doc.final.split.md"),
            
            # Files with special characters
            ("test-file.txt", "parse", "test-file.parse.md"),
            ("test_file.pdf", "split", "test_file.split.md"),
            ("test file.md", "finalize", "test_file.finalize.md")
        ]
        
        for input_name, phase, expected in test_cases:
            file_path = tmp_path / input_name
            markdown_path = get_markdown_path(file_path, phase)
            assert markdown_path.name == expected
            assert markdown_path.parent == file_path.parent 