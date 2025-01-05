"""Unit tests for path utilities."""

# Standard library
from pathlib import Path

# External dependencies
import pytest

# Internal imports
from nova.utils.path_utils import (
    ensure_parent_dirs,
    get_markdown_path,
    get_metadata_path,
    get_relative_path,
    get_safe_path,
    sanitize_filename,
)


@pytest.mark.unit
@pytest.mark.utils
class TestPathUtils:
    """Test path utility functions."""

    def test_sanitize_filename(self):
        """Test filename sanitization."""
        test_cases = [
            # Basic invalid characters
            ('file<>:"/\\|?*name.txt', "file_name_.txt"),
            ("file!@#$%^{}.txt", "file_.txt"),
            ("file\x00\x1f.txt", "file_.txt"),
            # Multiple spaces and underscores
            ("file   name.txt", "file_name.txt"),
            ("file___name.txt", "file_name.txt"),
            ("file _ name.txt", "file_name.txt"),
            # Leading/trailing dots and spaces
            (" file.txt", "file.txt"),
            ("file.txt.", "file.txt."),
            ("file.txt.", "file.txt."),
            # Empty or all invalid
            ("", "unnamed"),
            ("!@#$%^&*.txt", "unnamed_.txt"),
            # Unicode characters
            ("привет.txt", "privet.txt"),
            ("你好.txt", "unnamed.txt"),
        ]

        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert (
                result == expected
            ), f"Failed for input '{input_name}': expected '{expected}', got '{result}'"

    def test_empty_and_invalid_filenames(self):
        """Test edge cases for filename sanitization."""
        test_cases = [
            # Empty strings and whitespace
            ("", "unnamed"),
            (" ", "unnamed"),
            ("\t\n\r", "unnamed"),
            # Only dots
            (".", "unnamed"),
            ("..", "unnamed"),
            ("...", "unnamed"),
            # Only special characters
            ("!@#$%^&*()", "unnamed_"),
            ('<>:"/\\|?*', "unnamed_"),
            ("\x00\x1f\x7f", "unnamed_"),
            # Mixed special cases
            (" . ", "unnamed"),
            ("...txt...", "txt."),
            (".hidden", "hidden"),
            # Unicode edge cases
            ("\u200b\u200c\u200d", "unnamed"),  # Zero-width spaces
            ("\u0000\u0001\u001f", "unnamed_"),  # Control characters
            (
                "привет\x00世界.txt",
                "privet_unnamed.txt",
            ),  # Mixed scripts with control char
            # Extension edge cases
            ("file..txt", "file.txt"),
            ("file...txt...", "file.txt."),
            ("..hidden.txt..", "hidden.txt."),
        ]

        for input_name, expected in test_cases:
            result = sanitize_filename(input_name)
            assert (
                result == expected
            ), f"Failed for input '{input_name}': expected '{expected}', got '{result}'"

    def test_path_normalization(self, mock_fs):
        """Test path normalization."""
        # Create test directories
        base_dir = mock_fs["root"] / "test_paths"
        base_dir.mkdir()

        # Test absolute path
        test_path = base_dir / "subdir" / "file.txt"
        safe_path = get_safe_path(test_path)
        assert safe_path.is_absolute()
        assert safe_path.name == "file.txt"

        # Test relative path
        rel_path = get_safe_path(test_path, make_relative_to=base_dir)
        assert not rel_path.is_absolute()
        assert rel_path.name == "file.txt"
        assert rel_path.parts == ("subdir", "file.txt")

    def test_metadata_path(self, mock_fs):
        """Test metadata path generation."""
        file_path = mock_fs["input"] / "test.txt"
        metadata_path = get_metadata_path(file_path)
        assert metadata_path.name == "test.metadata.json"
        assert metadata_path.parent.resolve() == file_path.parent.resolve()

    def test_markdown_path(self, mock_fs):
        """Test markdown path generation."""
        file_path = mock_fs["input"] / "test.txt"
        markdown_path = get_markdown_path(file_path, "parse")
        assert markdown_path.name == "test.parse.md"
        assert markdown_path.parent.resolve() == file_path.parent.resolve()

    def test_relative_path(self, mock_fs):
        """Test relative path calculation."""
        # Create test directories
        base_dir = mock_fs["root"] / "test_paths"
        dir_a = base_dir / "a"
        dir_b = base_dir / "b"
        dir_c = dir_b / "c"
        dir_d = base_dir / "d"
        dir_e = dir_d / "e"

        for dir_path in [dir_a, dir_b, dir_c, dir_d, dir_e]:
            dir_path.mkdir(parents=True)

        # Test same directory
        file1 = dir_a / "file1.txt"
        file2 = dir_a / "file2.txt"
        assert get_relative_path(file1, file2) == "file2.txt"

        # Test different directories
        file3 = dir_c / "file3.txt"
        file4 = dir_e / "file4.txt"
        rel_path = get_relative_path(file3, file4)
        assert rel_path == "../../d/e/file4.txt"

        # Test special case for deep paths
        file5 = dir_c / "file5.txt"
        file6 = dir_e / "f.txt"
        rel_path = get_relative_path(file5, file6)
        assert rel_path == "../../e/f.txt"
